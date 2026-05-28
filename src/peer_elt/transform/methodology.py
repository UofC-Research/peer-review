from __future__ import annotations

"""Preregistered Study 1 scoring workflow.

This module implements the methodology-level operations from the planning
document:

- score preprint and published versions independently,
- retain all preregistered indicators V1-V10, including absent indicators,
- compute raw statistical rigour scores,
- compute indicator deltas and PRES at the matched-pair level,
- expose evidence rows for auditability, and
- flag zero scores for document-completeness review.

The scorer itself is injected so this workflow can use the conservative
rule-based scorer, a hybrid scorer, or a future adjudicated scorer without
changing the pair-level aggregation rules.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol

from peer_elt.transform.scoring import EvidenceSnippet, HybridScorecard, IndicatorScore

PREREGISTERED_INDICATORS: tuple[str, ...] = (
    "V1",
    "V2",
    "V3",
    "V4",
    "V5",
    "V6",
    "V7",
    "V8",
    "V9",
    "V10",
)


class SectionScorer(Protocol):
    """Protocol for objects that score manuscript sections."""

    def score(self, sections: Mapping[str, str]) -> HybridScorecard:
        """Return a scorecard for a manuscript version."""


@dataclass(frozen=True)
class VersionScorecard:
    """Scores and audit metadata for one manuscript version."""

    manuscript_id: str
    version: str
    document_format: str | None
    scores: tuple[IndicatorScore, ...]

    def as_dict(self) -> dict[str, IndicatorScore]:
        """Return indicator scores keyed by V1-V10."""
        return {score.indicator: score for score in self.scores}

    @property
    def raw_score(self) -> int:
        """Raw Statistical Rigour Score: sum of V1-V10 for this version."""
        return sum(score.score for score in self.scores)

    @property
    def zero_score_indicators(self) -> tuple[str, ...]:
        """Indicators scored 0 and therefore flagged for access verification."""
        return tuple(score.indicator for score in self.scores if score.score == 0)

    @property
    def needs_document_completeness_review(self) -> bool:
        """Whether this version needs human document-completeness review."""
        return bool(self.zero_score_indicators)

    def evidence_rows(self) -> list[dict[str, object]]:
        """Return one flat audit row per evidence snippet."""
        rows: list[dict[str, object]] = []
        for score in self.scores:
            for evidence in score.evidence:
                rows.append(_evidence_row(self, score, evidence))
        return rows


@dataclass(frozen=True)
class PairScorecard:
    """Matched manuscript-pair scoring output."""

    manuscript_id: str
    preprint: VersionScorecard
    published: VersionScorecard

    @property
    def indicator_deltas(self) -> dict[str, int]:
        """Return published-minus-preprint deltas for all V1-V10."""
        preprint_scores = self.preprint.as_dict()
        published_scores = self.published.as_dict()
        return {
            indicator: published_scores[indicator].score - preprint_scores[indicator].score
            for indicator in PREREGISTERED_INDICATORS
        }

    @property
    def pres(self) -> int:
        """Peer-Review Effect Score for the matched pair."""
        return self.published.raw_score - self.preprint.raw_score

    def to_record(self) -> dict[str, object]:
        """Return a flat pair-level record suitable for a table/DataFrame."""
        record: dict[str, object] = {
            "manuscript_id": self.manuscript_id,
            "preprint_document_format": self.preprint.document_format,
            "published_document_format": self.published.document_format,
            "preprint_raw_statistical_rigour": self.preprint.raw_score,
            "published_raw_statistical_rigour": self.published.raw_score,
            "PRES": self.pres,
            "preprint_needs_document_completeness_review": (
                self.preprint.needs_document_completeness_review
            ),
            "published_needs_document_completeness_review": (
                self.published.needs_document_completeness_review
            ),
        }

        preprint_scores = self.preprint.as_dict()
        published_scores = self.published.as_dict()
        deltas = self.indicator_deltas
        for indicator in PREREGISTERED_INDICATORS:
            record[f"{indicator}_preprint"] = preprint_scores[indicator].score
            record[f"{indicator}_published"] = published_scores[indicator].score
            record[f"{indicator}_delta"] = deltas[indicator]
        return record

    def evidence_rows(self) -> list[dict[str, object]]:
        """Return flat audit rows from both manuscript versions."""
        return self.preprint.evidence_rows() + self.published.evidence_rows()


def score_manuscript_version(
        manuscript_id: str,
        version: str,
        sections: Mapping[str, str],
        scorer: SectionScorer,
        document_format: str | None = None,
) -> VersionScorecard:
    """Score one manuscript version using the fixed V1-V10 workflow."""
    scorecard = scorer.score(sections)
    complete_scores = _complete_indicator_scores(scorecard.as_dict())
    return VersionScorecard(
        manuscript_id=manuscript_id,
        version=version,
        document_format=document_format,
        scores=complete_scores,
    )


def score_manuscript_pair(
        manuscript_id: str,
        preprint_sections: Mapping[str, str],
        published_sections: Mapping[str, str],
        scorer: SectionScorer,
        preprint_format: str | None = None,
        published_format: str | None = None,
) -> PairScorecard:
    """Score a matched preprint/published pair and compute deltas plus PRES."""
    preprint = score_manuscript_version(
        manuscript_id=manuscript_id,
        version="preprint",
        sections=preprint_sections,
        scorer=scorer,
        document_format=preprint_format,
    )
    published = score_manuscript_version(
        manuscript_id=manuscript_id,
        version="published",
        sections=published_sections,
        scorer=scorer,
        document_format=published_format,
    )
    return PairScorecard(
        manuscript_id=manuscript_id,
        preprint=preprint,
        published=published,
    )


def _complete_indicator_scores(
        scores: Mapping[str, IndicatorScore],
) -> tuple[IndicatorScore, ...]:
    """Materialize absent indicators as explicit 0 scores."""
    complete: list[IndicatorScore] = []
    for indicator in PREREGISTERED_INDICATORS:
        complete.append(
            scores.get(
                indicator,
                IndicatorScore(
                    indicator=indicator,
                    score=0,
                    rationale="No observable reporting content found",
                    evidence=(),
                ),
            )
        )
    return tuple(complete)


def _evidence_row(
        version_scorecard: VersionScorecard,
        score: IndicatorScore,
        evidence: EvidenceSnippet,
) -> dict[str, object]:
    """Build one flat evidence row."""
    return {
        "manuscript_id": version_scorecard.manuscript_id,
        "version": version_scorecard.version,
        "document_format": version_scorecard.document_format,
        "indicator": score.indicator,
        "score": score.score,
        "rationale": score.rationale,
        "section": evidence.section,
        "text": evidence.text,
        "pattern": evidence.pattern,
    }
