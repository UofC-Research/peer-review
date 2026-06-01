from __future__ import annotations

"""Scoring utilities for preregistered indicators of statistical reporting.

This module provides a small, conservative scoring system for manuscript text.

It supports two scoring modes:

- **Rule-based scoring** via preregistered regex cues (grouped by indicator and
  evidence level) applied to specific manuscript sections (e.g., ``"methods"``,
  ``"results"``).
- **Hybrid scoring** that optionally merges rule-based output with a model-based
  scorer, defaulting to conservative behavior when sources disagree.

Key concepts
------------
Indicator
    Short identifier for a preregistered variable/indicator (e.g., ``"V1"`` ...
    ``"V10"``).
Section
    Named slice of manuscript text (e.g., ``"methods"``, ``"results"``,
    ``"statements"``). Callers provide a mapping of section name to section text.
Score / Level
    Integer representing evidence strength for an indicator (higher usually
    means stronger or more specific evidence under preregistered rules).

Notes
-----
- Evidence is stored as short text snippets around matched regex spans.
- For each (indicator, pattern), at most the first 3 matches are retained.
- Hybrid merging prefers lower scores when rule and model disagree unless the
  model supplies high confidence.
"""

from dataclasses import dataclass, field
from itertools import chain
import re
from typing import Callable, Iterable, Mapping, Sequence


IndicatorName = str


@dataclass(frozen=True)
class EvidenceSnippet:
    """Short excerpt supporting an indicator score.

    Attributes
    ----------
    indicator : str
        Indicator identifier this snippet supports (e.g., ``"V3"``).
    section : str
        Section name where the evidence was found (e.g., ``"results"``).
    text : str
        Extracted text window around the match (trimmed).
    pattern : str
        Regex pattern responsible for the match (useful for auditing/debugging).
    """

    indicator: IndicatorName
    section: str
    text: str
    pattern: str


@dataclass(frozen=True)
class IndicatorScore:
    """Score for a single indicator, optionally with evidence and provenance.

    Attributes
    ----------
    indicator : str
        Indicator identifier (e.g., ``"V1"``).
    score : int
        Final chosen score for this indicator.
    rationale : str
        Human-readable reason for the chosen score.
    evidence : tuple[EvidenceSnippet, ...], default=()
        Evidence snippets supporting the score.
    rule_score : int | None, default=None
        Rule-based score, if available.
    model_score : int | None, default=None
        Model-based score, if available.
    model_confidence : float | None, default=None
        Model confidence, if available.
    """

    indicator: IndicatorName
    score: int
    rationale: str
    evidence: tuple[EvidenceSnippet, ...] = field(default_factory=tuple)
    rule_score: int | None = None
    model_score: int | None = None
    model_confidence: float | None = None


@dataclass(frozen=True)
class HybridScorecard:
    """Immutable collection of :class:`IndicatorScore` entries.

    Attributes
    ----------
    scores : tuple[IndicatorScore, ...]
        Scores contained in this scorecard.
    """

    scores: tuple[IndicatorScore, ...]

    def as_dict(self) -> dict[IndicatorName, IndicatorScore]:
        """Return scores keyed by indicator name.

        Returns
        -------
        dict[str, IndicatorScore]
            Mapping from indicator name to its score.
        """
        return {score.indicator: score for score in self.scores}


@dataclass(frozen=True)
class RulePattern:
    """Single regex rule used for rule-based scoring.

    Attributes
    ----------
    indicator : str
        Indicator identifier this rule supports.
    level : int
        Evidence level contributed by this rule when matched.
    section : str
        Section name to search within.
    pattern : str
        Regex pattern to apply (case-insensitive).
    """

    indicator: IndicatorName
    level: int
    section: str
    pattern: str


@dataclass(frozen=True)
class ModelPrediction:
    """Model-produced prediction for a single indicator.

    Attributes
    ----------
    indicator : str
        Indicator identifier.
    score : int
        Predicted score.
    confidence : float
        Model confidence for the predicted score.
    section : str
        Section where the evidence applies (must exist in the input mapping).
    evidence_text : str
        Evidence text (or snippet) supporting the prediction.
    """

    indicator: IndicatorName
    score: int
    confidence: float
    section: str
    evidence_text: str


@dataclass(frozen=True)
class _RuleEvaluation:
    indicator: IndicatorName
    level: int
    evidence: tuple[EvidenceSnippet, ...]


class RuleBasedScorer:
    """Conservative rule-based scorer using preregistered indicator cues.

    The scorer applies regex patterns (case-insensitive) to specified sections of
    a manuscript. For each indicator, the maximum matched level across its
    patterns becomes the indicator's rule score.

    Notes
    -----
    Evidence handling:

    - For each matched rule pattern, up to the first 3 matches are stored as
      :class:`EvidenceSnippet` instances.
    - Each snippet includes a window around the match (±80 characters).
    """

    def __init__(self, patterns: Iterable[RulePattern]) -> None:
        """Create a rule-based scorer.

        Parameters
        ----------
        patterns : Iterable[RulePattern]
            Rules defining indicator cues (indicator, level, section, regex).
        """
        self._patterns = tuple(patterns)

    def score(self, sections: Mapping[str, str]) -> dict[IndicatorName, IndicatorScore]:
        """Score all indicators supported by the configured rule patterns.

        Parameters
        ----------
        sections : Mapping[str, str]
            Mapping of section name to raw text.

        Returns
        -------
        dict[str, IndicatorScore]
            Mapping from indicator name to its score. Only indicators with at
            least one match are returned. Indicators with no evidence are
            omitted (callers may treat missing as score 0 if desired).
        """
        evaluations = tuple(
            evaluation
            for rule in self._patterns
            for evaluation in (_evaluate_rule(rule, sections.get(rule.section, "")),)
            if evaluation is not None
        )
        return {
            indicator: _indicator_score_from_rule_evaluations(indicator, evaluations)
            for indicator in _matched_indicators(evaluations)
        }


ModelScoringFn = Callable[[Mapping[str, str]], dict[IndicatorName, IndicatorScore]]


class ModelScorer:
    """Model-backed scorer converting predictions into indicator scores.

    Parameters
    ----------
    predictions : Sequence[ModelPrediction]
        Predictions to materialize into :class:`IndicatorScore` entries.
    rationale : str
        Rationale string attached to produced scores.
    """

    def __init__(self, predictions: Sequence[ModelPrediction], rationale: str) -> None:
        self._predictions = tuple(predictions)
        self._rationale = rationale

    def __call__(self, sections: Mapping[str, str]) -> dict[IndicatorName, IndicatorScore]:
        """Score indicators from model predictions.

        Parameters
        ----------
        sections : Mapping[str, str]
            Mapping of section name to text. Predictions referencing a section
            not present in this mapping are ignored.

        Returns
        -------
        dict[str, IndicatorScore]
            Mapping from indicator name to model-produced score.
        """
        return {
            prediction.indicator: _score_model_prediction(prediction, self._rationale)
            for prediction in self._predictions
            if prediction.section in sections
        }


class HybridScorer:
    """Hybrid scorer combining rule-based signals with optional model outputs.

    Combination strategy (conservative by default)
    ---------------------------------------------
    - If both rule and model score an indicator:
        - If model confidence >= ``override_confidence``, use the model score.
        - Otherwise, use ``min(rule_score, model_score)`` to avoid optimistic
          inflation.
    - If only one source provides a score, use it.
    - If neither provides a score, return 0 with rationale "No evidence found".

    Notes
    -----
    Evidence from rule and model is concatenated when both are present.
    """

    def __init__(
        self,
        rule_scorer: RuleBasedScorer,
        model_scorer: ModelScoringFn | None = None,
        override_confidence: float = 0.8,
    ) -> None:
        """Create a hybrid scorer.

        Parameters
        ----------
        rule_scorer : RuleBasedScorer
            Mandatory rule-based scorer.
        model_scorer : ModelScoringFn | None, default=None
            Optional callable returning model-produced indicator scores keyed by
            indicator name.
        override_confidence : float, default=0.8
            Confidence threshold above which the model may override conservative
            merging.
        """
        self._rule_scorer = rule_scorer
        self._model_scorer = model_scorer
        self._override_confidence = override_confidence

    def score(self, sections: Mapping[str, str]) -> HybridScorecard:
        """Compute a combined scorecard for the given manuscript sections.

        Parameters
        ----------
        sections : Mapping[str, str]
            Mapping of section name to raw text.

        Returns
        -------
        HybridScorecard
            Immutable scorecard containing merged indicator scores.
        """
        rule_scores = self._rule_scorer.score(sections)
        model_scores = self._model_scorer(sections) if self._model_scorer else {}
        combined = tuple(
            self._merge_scores(
                indicator,
                rule_scores.get(indicator),
                model_scores.get(indicator),
            )
            for indicator in sorted(set(rule_scores) | set(model_scores))
        )
        return HybridScorecard(combined)

    def _merge_scores(
        self,
        indicator: IndicatorName,
        rule_score: IndicatorScore | None,
        model_score: IndicatorScore | None,
    ) -> IndicatorScore:
        """Merge possibly-missing scores from rule and model sources.

        Parameters
        ----------
        indicator : str
            Indicator identifier.
        rule_score : IndicatorScore | None
            Rule-based score (if present).
        model_score : IndicatorScore | None
            Model-based score (if present).

        Returns
        -------
        IndicatorScore
            Merged score entry.
        """
        if rule_score and model_score:
            return self._merge_rule_and_model(indicator, rule_score, model_score)
        if rule_score:
            return rule_score
        if model_score:
            return model_score
        return IndicatorScore(indicator=indicator, score=0, rationale="No evidence found")

    def _merge_rule_and_model(
        self,
        indicator: IndicatorName,
        rule_score: IndicatorScore,
        model_score: IndicatorScore,
    ) -> IndicatorScore:
        """Merge scores when both sources produced output for an indicator.

        Parameters
        ----------
        indicator : str
            Indicator identifier.
        rule_score : IndicatorScore
            Rule-based score entry.
        model_score : IndicatorScore
            Model-based score entry.

        Returns
        -------
        IndicatorScore
            Merged score entry with combined evidence and provenance fields.
        """
        rule_value = rule_score.score
        model_value = model_score.score
        confidence = model_score.model_confidence or 0.0

        if confidence >= self._override_confidence:
            final_score = model_value
            rationale = "Model score used (high confidence)"
        else:
            final_score = min(rule_value, model_value)
            rationale = "Conservative merge (lower score)"

        evidence = rule_score.evidence + model_score.evidence
        return IndicatorScore(
            indicator=indicator,
            score=final_score,
            rationale=rationale,
            evidence=evidence,
            rule_score=rule_value,
            model_score=model_value,
            model_confidence=model_score.model_confidence,
        )


def _evaluate_rule(rule: RulePattern, text: str) -> _RuleEvaluation | None:
    if not text:
        return None

    matches = tuple(re.finditer(rule.pattern, text, flags=re.IGNORECASE))
    if not matches:
        return None

    return _RuleEvaluation(
        indicator=rule.indicator,
        level=rule.level,
        evidence=_evidence_snippets(rule, text, matches[:3]),
    )


def _evidence_snippets(
        rule: RulePattern,
        text: str,
        matches: Sequence[re.Match[str]],
) -> tuple[EvidenceSnippet, ...]:
    return tuple(
        EvidenceSnippet(
            indicator=rule.indicator,
            section=rule.section,
            text=text[max(match.start() - 80, 0): match.end() + 80].strip(),
            pattern=rule.pattern,
        )
        for match in matches
    )


def _matched_indicators(
        evaluations: Sequence[_RuleEvaluation],
) -> tuple[IndicatorName, ...]:
    return tuple(dict.fromkeys(evaluation.indicator for evaluation in evaluations))


def _indicator_score_from_rule_evaluations(
        indicator: IndicatorName,
        evaluations: Sequence[_RuleEvaluation],
) -> IndicatorScore:
    matching = tuple(
        evaluation for evaluation in evaluations if evaluation.indicator == indicator
    )
    level = max(evaluation.level for evaluation in matching)
    return IndicatorScore(
        indicator=indicator,
        score=level,
        rationale="Rule-based pattern match",
        evidence=tuple(
            chain.from_iterable(evaluation.evidence for evaluation in matching)
        ),
        rule_score=level,
    )


def _score_model_prediction(
        prediction: ModelPrediction,
        rationale: str,
) -> IndicatorScore:
    return IndicatorScore(
        indicator=prediction.indicator,
        score=prediction.score,
        rationale=rationale,
        evidence=(
            EvidenceSnippet(
                indicator=prediction.indicator,
                section=prediction.section,
                text=prediction.evidence_text,
                pattern="model-prediction",
            ),
        ),
        model_score=prediction.score,
        model_confidence=prediction.confidence,
    )


def default_rule_patterns() -> tuple[RulePattern, ...]:
    """Return the default preregistered rule patterns.

    Returns
    -------
    tuple[RulePattern, ...]
        Default patterns used by :class:`RuleBasedScorer`.

    Notes
    -----
    This is a baseline heuristic implementation: each indicator has two levels
    of evidence and is searched in a specific section. Callers may supply their
    own patterns to :class:`RuleBasedScorer` to customize behavior.
    """
    return (
        RulePattern(
            "V1",
            1,
            "results",
            r"\b(effect|estimate|odds ratio|hazard ratio|risk ratio|beta|coef)\b",
        ),
        RulePattern(
            "V1",
            2,
            "results",
            r"\b(odds ratio|hazard ratio|risk ratio|beta|coef)[^\n]{0,40}\b\d+",
        ),
        RulePattern("V2", 1, "results", r"\b(standard error|se|confidence interval|credible interval)\b"),
        RulePattern("V2", 2, "results", r"\b(95%|CI|CrI)\b"),
        RulePattern("V3", 1, "results", r"\bp\s*[<≤]\s*0\.\d+"),
        RulePattern("V3", 2, "results", r"\bp\s*=\s*0\.\d+"),
        RulePattern("V4", 1, "methods", r"\b(sample size|power calculation|power analysis)\b"),
        RulePattern("V4", 2, "methods", r"\b(power|alpha|effect size)\b"),
        RulePattern("V5", 1, "methods", r"\b(regression|model|anova|cox|glm)\b"),
        RulePattern("V5", 2, "methods", r"\b(covariate|adjusted for|assumption|interaction)\b"),
        RulePattern(
            "V6",
            1,
            "methods",
            r"\b(multiple comparisons|multiplicity|multiple testing)\b",
        ),
        RulePattern("V6", 2, "methods", r"\b(bonferroni|fdr|holm)\b"),
        RulePattern("V7", 1, "results", r"\b(sensitivity analysis|robustness check)\b"),
        RulePattern("V7", 2, "results", r"\b(alternative model|subgroup analysis|leave-one-out)\b"),
        RulePattern("V8", 1, "methods", r"\b(missing data|missingness)\b"),
        RulePattern("V8", 2, "methods", r"\b(imputation|complete case|multiple imputation)\b"),
        RulePattern("V9", 1, "statements", r"\b(data availability|code availability|supplementary material)\b"),
        RulePattern("V9", 2, "statements", r"\b(github|osf|zenodo|dryad|figshare)\b"),
        RulePattern("V10", 1, "methods", r"\b(flow diagram|study design|protocol)\b"),
        RulePattern("V10", 2, "methods", r"\b(consort|strobe|prisma)\b"),
    )
