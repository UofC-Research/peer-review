from __future__ import annotations

"""
Tests for the scoring subsystem.

These tests focus on the *behavioral contract* of the scorers in
`peer_elt.transform.scoring` rather than the exact implementation details:

- `RuleBasedScorer` should detect preregistered indicator cues (via regex rules)
  and emit scores + evidence snippets.
- `HybridScorer` should combine rule-based and model-based scores conservatively:
  - If model confidence is *below* the override threshold, it should prefer the
    lower (more conservative) score when rule/model disagree.
  - If model confidence is *at or above* the threshold, it may override with the
    model score.

Note:
These are unit tests with small synthetic "paper sections" (methods/results/
statements). They intentionally avoid needing any external data or ML model.
"""

from peer_elt.transform.scoring import (
    EvidenceSnippet,
    HybridScorer,
    IndicatorScore,
    RuleBasedScorer,
    ModelPrediction,
    ModelScorer,
    default_rule_patterns,
)


def test_rule_based_scoring_hits_all_indicators() -> None:
    """
    Integration-style unit test for the default rule patterns.

    Given a set of section texts containing at least one cue for each indicator
    V1..V10, the rule-based scorer should:
      - return an `IndicatorScore` for every indicator,
      - assign the highest matched level (here we expect level 2 for all),
      - include evidence snippets for traceability.
    """
    sections = {
        "methods": (
            "We ran a regression model adjusted for covariate A with interaction terms. "
            "A power calculation assumed alpha 0.05 and effect size 0.4. "
            "Multiplicity was addressed using Bonferroni correction. "
            "Missing data handled via multiple imputation. "
            "CONSORT flow diagram included."
        ),
        "results": (
            "Primary effect estimate: odds ratio 1.45 with 95% CI 1.10-1.90, p = 0.02. "
            "Sensitivity analysis included an alternative model."
        ),
        "statements": "Data availability on GitHub with code availability statement.",
    }

    scorer = RuleBasedScorer(default_rule_patterns())
    scores = scorer.score(sections)

    for indicator in ("V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"):
        assert indicator in scores
        assert scores[indicator].score == 2
        assert scores[indicator].evidence


def test_hybrid_scoring_prefers_lower_score_when_low_confidence() -> None:
    """
    When both rule-based and model-based scores exist for an indicator and the
    model confidence is below the override threshold, the hybrid scorer should
    behave conservatively and select the *lower* score.

    This protects against over-scoring when the model is uncertain.
    """
    sections = {"results": "odds ratio 1.2", "methods": "", "statements": ""}
    rule_scorer = RuleBasedScorer(default_rule_patterns())

    def model_scorer(_sections: dict[str, str]):
        return {
            "V1": IndicatorScore(
                indicator="V1",
                score=1,
                rationale="Model suggestion",
                evidence=(EvidenceSnippet("V1", "results", "model", "model"),),
                model_score=1,
                model_confidence=0.4,
            )
        }

    hybrid = HybridScorer(rule_scorer, model_scorer=model_scorer, override_confidence=0.8)
    scorecard = hybrid.score(sections).as_dict()

    assert scorecard["V1"].score == 1
    assert scorecard["V1"].rationale == "Conservative merge (lower score)"


def test_hybrid_scoring_allows_high_confidence_override() -> None:
    """
    When model confidence meets/exceeds the override threshold, the hybrid scorer
    should allow the model to override rule-based scoring.

    This enables a model to "upgrade" an indicator score when it is sufficiently
    confident.
    """
    sections = {"results": "odds ratio 1.2", "methods": "", "statements": ""}
    rule_scorer = RuleBasedScorer(default_rule_patterns())

    def model_scorer(_sections: dict[str, str]):
        return {
            "V1": IndicatorScore(
                indicator="V1",
                score=2,
                rationale="Model suggestion",
                evidence=(EvidenceSnippet("V1", "results", "model", "model"),),
                model_score=2,
                model_confidence=0.95,
            )
        }

    hybrid = HybridScorer(rule_scorer, model_scorer=model_scorer, override_confidence=0.8)
    scorecard = hybrid.score(sections).as_dict()

    assert scorecard["V1"].score == 2
    assert scorecard["V1"].rationale == "Model score used (high confidence)"

def test_model_scorer_builds_indicator_scores_from_predictions() -> None:
    sections = {"methods": "model text", "results": "results text", "statements": "data availability"}
    predictions = [
        ModelPrediction(indicator="V1", score=2, confidence=0.92, section="results", evidence_text="odds ratio 1.2"),
        ModelPrediction(indicator="V2", score=1, confidence=0.61, section="results", evidence_text="95% CI"),
    ]

    model_scorer = ModelScorer(predictions=predictions, rationale="ML classifier output")
    scores = model_scorer(sections)

    assert scores["V1"].score == 2
    assert scores["V1"].model_confidence == 0.92
    assert scores["V1"].rationale == "ML classifier output"
    assert scores["V1"].evidence
    assert scores["V2"].score == 1