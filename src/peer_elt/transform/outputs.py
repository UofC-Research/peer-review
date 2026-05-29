from __future__ import annotations

"""Output repository for methodology scoring artifacts."""

from dataclasses import dataclass
from typing import Iterable, Protocol

import pandas as pd

from peer_elt.config import PipelineConfig
from peer_elt.interfaces import Storage
from peer_elt.pipeline import write_outputs
from peer_elt.transform.methodology import PairScorecard

PAIR_SCORE_TABLE = "methodology_pair_scores"
EVIDENCE_TABLE = "methodology_evidence_rows"

PAIR_SCORE_COLUMNS: tuple[str, ...] = (
    "manuscript_id",
    "preprint_document_format",
    "published_document_format",
    "preprint_raw_statistical_rigour",
    "published_raw_statistical_rigour",
    "PRES",
    "preprint_needs_document_completeness_review",
    "published_needs_document_completeness_review",
)

EVIDENCE_COLUMNS: tuple[str, ...] = (
    "manuscript_id",
    "version",
    "document_format",
    "indicator",
    "score",
    "rationale",
    "section",
    "text",
    "pattern",
)


@dataclass(frozen=True)
class MethodologyOutputFrames:
    """Tabular methodology outputs prepared for storage and R analysis.

    Attributes
    ----------
    pair_scores : pandas.DataFrame
        Pair-level ``methodology_pair_scores`` records consumed by the R
        analysis layer.
    evidence_rows : pandas.DataFrame
        Audit-level ``methodology_evidence_rows`` records.
    """

    pair_scores: pd.DataFrame
    evidence_rows: pd.DataFrame


class MethodologyOutputRepository(Protocol):
    """Repository interface for persisting fixed methodology score outputs."""

    def save(self, pair_scorecards: Iterable[PairScorecard]) -> MethodologyOutputFrames:
        """Persist scorecards and return the materialized DataFrames.

        Parameters
        ----------
        pair_scorecards : Iterable[peer_elt.transform.methodology.PairScorecard]
            Fixed matched-pair scorecards to persist.

        Returns
        -------
        MethodologyOutputFrames
            Materialized pair-score and evidence DataFrames.
        """


class StorageMethodologyOutputRepository:
    """Persist methodology outputs through the configured storage/output layer.

    Parameters
    ----------
    storage : peer_elt.interfaces.Storage
        Storage backend used for named output tables.
    config : peer_elt.config.PipelineConfig
        Pipeline configuration used to determine output paths and CSV behavior.
    """

    def __init__(self, storage: Storage, config: PipelineConfig) -> None:
        self._storage = storage
        self._config = config

    def save(self, pair_scorecards: Iterable[PairScorecard]) -> MethodologyOutputFrames:
        """Write pair-score and evidence tables to files and storage.

        Parameters
        ----------
        pair_scorecards : Iterable[peer_elt.transform.methodology.PairScorecard]
            Fixed matched-pair scorecards to persist.

        Returns
        -------
        MethodologyOutputFrames
            DataFrames written to storage and configured output files.
        """
        frames = build_methodology_output_frames(pair_scorecards)
        write_outputs(self._storage, self._config, frames.pair_scores, PAIR_SCORE_TABLE)
        write_outputs(self._storage, self._config, frames.evidence_rows, EVIDENCE_TABLE)
        return frames


def build_methodology_output_frames(
        pair_scorecards: Iterable[PairScorecard],
) -> MethodologyOutputFrames:
    """Build stable DataFrames from methodology scorecards.

    Parameters
    ----------
    pair_scorecards : Iterable[peer_elt.transform.methodology.PairScorecard]
        Fixed matched-pair scorecards.

    Returns
    -------
    MethodologyOutputFrames
        Pair-score and evidence DataFrames. Empty inputs still produce stable
        schemas.
    """
    scorecards = tuple(pair_scorecards)
    pair_records = [scorecard.to_record() for scorecard in scorecards]
    evidence_records = [
        row for scorecard in scorecards for row in scorecard.evidence_rows()
    ]

    pair_scores = pd.DataFrame.from_records(pair_records)
    evidence_rows = pd.DataFrame.from_records(evidence_records)

    if pair_scores.empty:
        pair_scores = pd.DataFrame(columns=_pair_score_columns())
    if evidence_rows.empty:
        evidence_rows = pd.DataFrame(columns=EVIDENCE_COLUMNS)

    return MethodologyOutputFrames(
        pair_scores=pair_scores,
        evidence_rows=evidence_rows,
    )


def _pair_score_columns() -> tuple[str, ...]:
    """Return the stable empty-schema columns for pair-score records.

    Returns
    -------
    tuple[str, ...]
        Column names for ``methodology_pair_scores``.
    """
    indicators = tuple(f"V{index}" for index in range(1, 11))
    indicator_columns = tuple(
        column
        for indicator in indicators
        for column in (
            f"{indicator}_preprint",
            f"{indicator}_published",
            f"{indicator}_delta",
        )
    )
    return PAIR_SCORE_COLUMNS + indicator_columns


__all__ = [
    "EVIDENCE_TABLE",
    "MethodologyOutputFrames",
    "MethodologyOutputRepository",
    "PAIR_SCORE_TABLE",
    "StorageMethodologyOutputRepository",
    "build_methodology_output_frames",
]
