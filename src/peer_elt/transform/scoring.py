from __future__ import annotations

"""Scoring utilities for preregistered indicators of statistical reporting.

This module provides a small, *conservative* scoring system for manuscript text:

- **Rule-based scoring**: apply preregistered regex cues (grouped by indicator and level)
  to specific manuscript sections (e.g., "methods", "results").
- **Hybrid scoring**: optionally merge rule-based scores with a model-based scorer while
  defaulting to conservative behavior when sources disagree.

Key concepts
------------
Indicator
    A short identifier for a preregistered variable/indicator (e.g., "V1"..."V10").

Section
    A named slice of manuscript text (e.g., "methods", "results", "statements"). Callers
    pass a mapping of section name -> section text.

Level / Score
    An integer representing the strength/strictness of evidence for an indicator, where
    higher usually means "more specific/stronger evidence" under preregistered rules.

Design notes
------------
- Evidence is stored as short text snippets around matched regex spans.
- For each (indicator, pattern) we keep at most the first 3 matches to avoid bloated output.
- Hybrid merging prefers *lower* scores when rule and model disagree, unless the model
  supplies high confidence.
"""

from dataclasses import dataclass, field
import re
from typing import Callable, Iterable, Mapping


IndicatorName = str


@dataclass(frozen=True)
class EvidenceSnippet:
    """A short excerpt supporting an indicator score.

    Attributes
    ----------
    indicator:
        Indicator identifier this snippet supports (e.g., "V3").
    section:
        Section name where the evidence was found (e.g., "results").
    text:
        Extracted text window around the match (trimmed).
    pattern:
        Regex pattern responsible for the match (useful for auditing/debugging).
    """

    indicator: IndicatorName
    section: str
    text: str
    pattern: str


@dataclass(frozen=True)
class IndicatorScore:
    indicator: IndicatorName
    score: int
    rationale: str
    evidence: tuple[EvidenceSnippet, ...] = field(default_factory=tuple)
    rule_score: int | None = None
    model_score: int | None = None
    model_confidence: float | None = None


@dataclass(frozen=True)
class HybridScorecard:
    """Immutable collection of `IndicatorScore` entries."""

    scores: tuple[IndicatorScore, ...]

    def as_dict(self) -> dict[IndicatorName, IndicatorScore]:
        """Return scores keyed by indicator name for convenient lookup."""
        return {score.indicator: score for score in self.scores}


@dataclass(frozen=True)
class RulePattern:
    indicator: IndicatorName
    level: int
    section: str
    pattern: str


class RuleBasedScorer:
    """Conservative rule-based scorer using preregistered indicator cues.

    The scorer applies regex patterns (case-insensitive) to specified sections of a manuscript.
    For each indicator, the *maximum* matched level across its patterns becomes the indicator's
    rule score.

    Evidence handling
    -----------------
    - For each matched rule pattern, up to the first 3 matches are stored as `EvidenceSnippet`s.
    - Each snippet includes a small window around the match (±80 characters).
    """

    def __init__(self, patterns: Iterable[RulePattern]) -> None:
        """Create a rule-based scorer.

        Parameters
        ----------
        patterns:
            Iterable of `RulePattern` objects defining indicator cues.
        """
        self._patterns = tuple(patterns)

    def score(self, sections: Mapping[str, str]) -> dict[IndicatorName, IndicatorScore]:
        """Score all indicators supported by the configured rule patterns.

        Parameters
        ----------
        sections:
            Mapping of section name to raw text.

        Returns
        -------
        dict[IndicatorName, IndicatorScore]
            Only indicators with at least one match are returned. Indicators with no evidence
            are omitted (callers can treat missing as score 0 if desired).
        """
        scores: dict[IndicatorName, IndicatorScore] = {}
        evidence_by_indicator: dict[IndicatorName, list[EvidenceSnippet]] = {}
        level_by_indicator: dict[IndicatorName, int] = {}

        for rule in self._patterns:
            text = sections.get(rule.section, "")
            if not text:
                continue
            matches = list(re.finditer(rule.pattern, text, flags=re.IGNORECASE))
            if not matches:
                continue
            evidence_by_indicator.setdefault(rule.indicator, [])
            for match in matches[:3]:
                snippet = text[max(match.start() - 80, 0) : match.end() + 80]
                evidence_by_indicator[rule.indicator].append(
                    EvidenceSnippet(
                        indicator=rule.indicator,
                        section=rule.section,
                        text=snippet.strip(),
                        pattern=rule.pattern,
                    )
                )
            previous = level_by_indicator.get(rule.indicator, 0)
            level_by_indicator[rule.indicator] = max(previous, rule.level)

        for indicator, level in level_by_indicator.items():
            scores[indicator] = IndicatorScore(
                indicator=indicator,
                score=level,
                rationale="Rule-based pattern match",
                evidence=tuple(evidence_by_indicator.get(indicator, [])),
                rule_score=level,
            )

        return scores


ModelScoringFn = Callable[[Mapping[str, str]], dict[IndicatorName, IndicatorScore]]


class HybridScorer:
    """Hybrid scorer combining rule-based signals with model outputs.

    Combination strategy (conservative by default)
    ---------------------------------------------
    - If both rule and model score an indicator:
        - If model confidence >= `override_confidence`, use the model score.
        - Otherwise, use `min(rule_score, model_score)` to avoid optimistic inflation.
    - If only one source provides a score, use it.
    - If neither provides a score, return 0 with rationale "No evidence found".

    Notes
    -----
    - Evidence from rule and model is concatenated when both are present.
    - This class does not validate the semantic meaning of score levels; it assumes both
      sources use a compatible integer scale.
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
        rule_scorer:
            Mandatory rule-based scorer.
        model_scorer:
            Optional callable returning model-produced `IndicatorScore`s keyed by indicator.
        override_confidence:
            Confidence threshold above which the model may override conservative merging.
        """
        self._rule_scorer = rule_scorer
        self._model_scorer = model_scorer
        self._override_confidence = override_confidence

    def score(self, sections: Mapping[str, str]) -> HybridScorecard:
        """Compute a combined scorecard for the given manuscript sections."""
        rule_scores = self._rule_scorer.score(sections)
        model_scores = self._model_scorer(sections) if self._model_scorer else {}
        indicators = set(rule_scores) | set(model_scores)
        combined: list[IndicatorScore] = []

        for indicator in sorted(indicators):
            rule_score = rule_scores.get(indicator)
            model_score = model_scores.get(indicator)
            combined.append(self._merge_scores(indicator, rule_score, model_score))

        return HybridScorecard(tuple(combined))

    def _merge_scores(
        self,
        indicator: IndicatorName,
        rule_score: IndicatorScore | None,
        model_score: IndicatorScore | None,
    ) -> IndicatorScore:
        """Merge possibly-missing scores from rule and model sources."""
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
        """Merge scores when both sources produced an output for an indicator."""
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


def default_rule_patterns() -> tuple[RulePattern, ...]:
    """Return the default preregistered rule patterns.

    These patterns are intended as a baseline heuristic implementation: each indicator has
    two levels of evidence and is searched in a specific section. Callers may supply their
    own patterns to `RuleBasedScorer` if they need to customize or extend behavior.
    """
    return (
        RulePattern("V1", 1, "results", r"\b(effect|estimate|odds ratio|hazard ratio|risk ratio|beta|coef)\b"),
        RulePattern("V1", 2, "results", r"\b(odds ratio|hazard ratio|risk ratio|beta|coef)[^\n]{0,40}\b\d+"),
        RulePattern("V2", 1, "results", r"\b(standard error|se|confidence interval|credible interval)\b"),
        RulePattern("V2", 2, "results", r"\b(95%|CI|CrI)\b"),
        RulePattern("V3", 1, "results", r"\bp\s*[<≤]\s*0\.\d+"),
        RulePattern("V3", 2, "results", r"\bp\s*=\s*0\.\d+"),
        RulePattern("V4", 1, "methods", r"\b(sample size|power calculation|power analysis)\b"),
        RulePattern("V4", 2, "methods", r"\b(power|alpha|effect size)\b"),
        RulePattern("V5", 1, "methods", r"\b(regression|model|anova|cox|glm)\b"),
        RulePattern("V5", 2, "methods", r"\b(covariate|adjusted for|assumption|interaction)\b"),
        RulePattern("V6", 1, "methods", r"\b(multiple comparisons|multiplicity|adjusted)\b"),
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
