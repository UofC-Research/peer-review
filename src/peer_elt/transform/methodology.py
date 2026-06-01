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

from peer_elt.transform.adapters import MethodologySectionAdapter, SectionAdapter
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
    """Protocol for objects that score manuscript sections.

    Notes
    -----
    This protocol matches scorer objects such as
    :class:`peer_elt.transform.scoring.HybridScorer`. It is kept minimal so
    future adjudicated or model-backed scorers can be injected without changing
    the methodology aggregation layer.
    """

    def score(self, sections: Mapping[str, str]) -> HybridScorecard:
        """Return a scorecard for a manuscript version.

        Parameters
        ----------
        sections : Mapping[str, str]
            Canonical manuscript sections keyed by names such as ``methods``,
            ``results``, and ``statements``.

        Returns
        -------
        peer_elt.transform.scoring.HybridScorecard
            Indicator-level scores and evidence for one manuscript version.
        """


class MethodologyScoringWorkflow:
    """Score parsed manuscript pairs through injected adapter/scorer strategies.

    Parameters
    ----------
    scorer : SectionScorer
        Scorer used after manuscript documents are normalized to canonical
        sections.
    section_adapter : peer_elt.transform.adapters.SectionAdapter | None, default=None
        Adapter strategy used to convert parsed documents or section mappings
        into ``methods``, ``results``, and ``statements`` sections.
    """

    def __init__(
            self,
            scorer: SectionScorer,
            section_adapter: SectionAdapter | None = None,
    ) -> None:
        self._scorer = scorer
        self._section_adapter = section_adapter or MethodologySectionAdapter()

    def score_pair(
            self,
            manuscript_id: str,
            preprint_document,
            published_document,
            preprint_format: str | None = None,
            published_format: str | None = None,
    ) -> "PairScorecard":
        """Score a matched pair from parsed document objects or section mappings.

        Parameters
        ----------
        manuscript_id : str
            Stable identifier for the matched manuscript pair.
        preprint_document
            Parsed preprint document or section mapping accepted by the
            configured section adapter.
        published_document
            Parsed published-article document or section mapping accepted by
            the configured section adapter.
        preprint_format : str | None, default=None
            Full-text format used for the preprint version when known.
        published_format : str | None, default=None
            Full-text format used for the published version when known.

        Returns
        -------
        PairScorecard
            Matched-pair scorecard with V1-V10 scores, deltas, PRES, and
            evidence rows.
        """
        preprint_sections = self._section_adapter.to_sections(preprint_document)
        published_sections = self._section_adapter.to_sections(published_document)
        return score_manuscript_pair(
            manuscript_id=manuscript_id,
            preprint_sections=preprint_sections,
            published_sections=published_sections,
            scorer=self._scorer,
            preprint_format=preprint_format,
            published_format=published_format,
        )


@dataclass(frozen=True)
class VersionScorecard:
    """Scores and audit metadata for one manuscript version.

    Attributes
    ----------
    manuscript_id : str
        Stable identifier for the matched manuscript pair.
    version : str
        Manuscript version label, typically ``"preprint"`` or ``"published"``.
    document_format : str | None
        Full-text format used for scoring when known.
    scores : tuple[peer_elt.transform.scoring.IndicatorScore, ...]
        Complete V1-V10 score entries for this manuscript version.
    """

    manuscript_id: str
    version: str
    document_format: str | None
    scores: tuple[IndicatorScore, ...]

    def as_dict(self) -> dict[str, IndicatorScore]:
        """Return indicator scores keyed by V1-V10.

        Returns
        -------
        dict[str, peer_elt.transform.scoring.IndicatorScore]
            Indicator score mapping.
        """
        return {score.indicator: score for score in self.scores}

    @property
    def raw_score(self) -> int:
        """Raw Statistical Rigour Score for this version.

        Returns
        -------
        int
            Sum of V1-V10 scores.
        """
        return sum(score.score for score in self.scores)

    @property
    def zero_score_indicators(self) -> tuple[str, ...]:
        """Indicators scored 0 and flagged for access verification.

        Returns
        -------
        tuple[str, ...]
            Indicator names with score 0.
        """
        return tuple(score.indicator for score in self.scores if score.score == 0)

    @property
    def needs_document_completeness_review(self) -> bool:
        """Whether this version needs document-completeness review.

        Returns
        -------
        bool
            True when any V1-V10 indicator is scored 0.
        """
        return bool(self.zero_score_indicators)

    def evidence_rows(self) -> list[dict[str, object]]:
        """Return one flat audit row per evidence snippet.

        Returns
        -------
        list[dict[str, object]]
            Evidence rows containing manuscript, version, indicator, score,
            section, text, and provenance fields.
        """
        return [
            _evidence_row(self, score, evidence)
            for score in self.scores
            for evidence in score.evidence
        ]


@dataclass(frozen=True)
class PairScorecard:
    """Matched manuscript-pair scoring output.

    Attributes
    ----------
    manuscript_id : str
        Stable identifier for the matched pair.
    preprint : VersionScorecard
        Scorecard for the selected preprint version.
    published : VersionScorecard
        Scorecard for the matched published version.
    """

    manuscript_id: str
    preprint: VersionScorecard
    published: VersionScorecard

    @property
    def indicator_deltas(self) -> dict[str, int]:
        """Return published-minus-preprint deltas for all V1-V10.

        Returns
        -------
        dict[str, int]
            Mapping from indicator name to ``published - preprint`` score.
        """
        preprint_scores = self.preprint.as_dict()
        published_scores = self.published.as_dict()
        return {
            indicator: published_scores[indicator].score - preprint_scores[indicator].score
            for indicator in PREREGISTERED_INDICATORS
        }

    @property
    def pres(self) -> int:
        """Peer-Review Effect Score for the matched pair.

        Returns
        -------
        int
            Published raw score minus preprint raw score.
        """
        return self.published.raw_score - self.preprint.raw_score

    def to_record(self) -> dict[str, object]:
        """Return a flat pair-level record suitable for tabular storage.

        Returns
        -------
        dict[str, object]
            Table-ready pair score record containing raw scores, PRES, V1-V10
            scores, V1-V10 deltas, document formats, and review flags.
        """
        preprint_scores = self.preprint.as_dict()
        published_scores = self.published.as_dict()
        deltas = self.indicator_deltas

        base_record: dict[str, object] = {
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

        indicator_record = {
            column: value
            for indicator in PREREGISTERED_INDICATORS
            for column, value in (
                (f"{indicator}_preprint", preprint_scores[indicator].score),
                (f"{indicator}_published", published_scores[indicator].score),
                (f"{indicator}_delta", deltas[indicator]),
            )
        }
        return {**base_record, **indicator_record}

    def evidence_rows(self) -> list[dict[str, object]]:
        """Return flat audit rows from both manuscript versions.

        Returns
        -------
        list[dict[str, object]]
            Concatenated preprint and published evidence rows.
        """
        return self.preprint.evidence_rows() + self.published.evidence_rows()


def score_manuscript_version(
        manuscript_id: str,
        version: str,
        sections: Mapping[str, str],
        scorer: SectionScorer,
        document_format: str | None = None,
) -> VersionScorecard:
    """Score one manuscript version using the fixed V1-V10 workflow.

    Parameters
    ----------
    manuscript_id : str
        Stable identifier for the matched manuscript pair.
    version : str
        Version label, typically ``"preprint"`` or ``"published"``.
    sections : Mapping[str, str]
        Canonical manuscript sections to score.
    scorer : SectionScorer
        Scorer object used to produce indicator evidence and scores.
    document_format : str | None, default=None
        Full-text format used for scoring when known.

    Returns
    -------
    VersionScorecard
        Complete V1-V10 scorecard for one manuscript version.
    """
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
    """Score a matched preprint/published pair and compute deltas plus PRES.

    Parameters
    ----------
    manuscript_id : str
        Stable identifier for the matched manuscript pair.
    preprint_sections : Mapping[str, str]
        Canonical sections for the selected preprint version.
    published_sections : Mapping[str, str]
        Canonical sections for the published article version.
    scorer : SectionScorer
        Scorer object applied independently to both versions.
    preprint_format : str | None, default=None
        Full-text format used for the preprint version when known.
    published_format : str | None, default=None
        Full-text format used for the published version when known.

    Returns
    -------
    PairScorecard
        Matched-pair scorecard with raw scores, deltas, PRES, and evidence.
    """
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
    """Materialize absent indicators as explicit 0 scores.

    Parameters
    ----------
    scores : Mapping[str, peer_elt.transform.scoring.IndicatorScore]
        Score mapping returned by the injected scorer.

    Returns
    -------
    tuple[peer_elt.transform.scoring.IndicatorScore, ...]
        Complete V1-V10 score tuple in preregistered order.
    """
    return tuple(
        scores.get(
            indicator,
            IndicatorScore(
                indicator=indicator,
                score=0,
                rationale="No observable reporting content found",
                evidence=(),
            ),
        )
        for indicator in PREREGISTERED_INDICATORS
    )


def _evidence_row(
        version_scorecard: VersionScorecard,
        score: IndicatorScore,
        evidence: EvidenceSnippet,
) -> dict[str, object]:
    """Build one flat evidence row.

    Parameters
    ----------
    version_scorecard : VersionScorecard
        Version-level scorecard providing manuscript metadata.
    score : peer_elt.transform.scoring.IndicatorScore
        Indicator score associated with the evidence snippet.
    evidence : peer_elt.transform.scoring.EvidenceSnippet
        Evidence snippet to flatten.

    Returns
    -------
    dict[str, object]
        Audit-ready evidence record.
    """
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
