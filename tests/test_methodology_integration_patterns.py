from __future__ import annotations

from pathlib import Path

import pandas as pd

from peer_elt.config import (
    OutputConfig,
    PipelineConfig,
    RetryConfig,
    SourceConfig,
    StorageConfig,
    TransformConfig,
)
from peer_elt.interfaces import Storage
from peer_elt.parse.models import ArticleDocument, GrobidResult, ParsedDocument
from peer_elt.transform.adapters import MethodologySectionAdapter
from peer_elt.transform.methodology import MethodologyScoringWorkflow
from peer_elt.transform.outputs import (
    EVIDENCE_TABLE,
    PAIR_SCORE_TABLE,
    StorageMethodologyOutputRepository,
    build_methodology_output_frames,
)
from peer_elt.transform.scoring import (
    HybridScorer,
    RuleBasedScorer,
    default_rule_patterns,
)


def _scorer() -> HybridScorer:
    return HybridScorer(RuleBasedScorer(default_rule_patterns()))


def _config(output_dir: Path) -> PipelineConfig:
    return PipelineConfig(
        sources=[
            SourceConfig(
                name="biorxiv",
                server="biorxiv",
                date_from="2023-01-01",
                date_to="2023-01-02",
            )
        ],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir=str(output_dir), write_csv=True),
        transform=TransformConfig(),
        retry=RetryConfig(),
    )


def test_section_adapter_normalizes_parsed_document_sections() -> None:
    parsed = ParsedDocument(
        source_path=Path("paper.pdf"),
        grobid=GrobidResult(
            tei_xml="<tei />",
            bibliography_xml=None,
            section_hierarchy={},
        ),
        blocks=(),
        sections={
            "Materials and Methods": "We used a regression model.",
            "Findings": "The odds ratio was 1.45.",
            "Data availability": "Data availability is provided on GitHub.",
        },
        features={},
        embeddings={},
    )

    sections = MethodologySectionAdapter().to_sections(parsed)

    assert sections["methods"] == "We used a regression model."
    assert sections["results"] == "The odds ratio was 1.45."
    assert sections["statements"] == "Data availability is provided on GitHub."


def test_article_adapter_extracts_headed_sections_for_scoring() -> None:
    article = ArticleDocument(
        source_url="https://example.org/published",
        html="<html />",
        text=(
            "Methods\n"
            "We used a regression model adjusted for covariate A.\n"
            "Results\n"
            "The odds ratio was 1.45 with 95% CI 1.10-1.90, p = 0.02.\n"
            "Statements\n"
            "Data availability is provided on GitHub."
        ),
        features={},
        embeddings={},
    )

    sections = MethodologySectionAdapter().to_sections(article)

    assert "adjusted for covariate" in sections["methods"]
    assert "95% CI" in sections["results"]
    assert "GitHub" in sections["statements"]


def test_methodology_workflow_scores_parsed_pair_through_adapter_strategy() -> None:
    workflow = MethodologyScoringWorkflow(_scorer())
    preprint = {
        "Materials and Methods": "We used a regression model.",
        "Findings": "The odds ratio was 1.45.",
    }
    published = {
        "Materials and Methods": (
            "We used a regression model adjusted for covariate A. "
            "A power calculation assumed alpha 0.05 and effect size 0.4."
        ),
        "Results": "The odds ratio was 1.45 with 95% CI 1.10-1.90, p = 0.02.",
        "Data availability": "Data availability is provided on GitHub.",
    }

    pair = workflow.score_pair(
        manuscript_id="biorxiv:10.1101/example",
        preprint_document=preprint,
        published_document=published,
        preprint_format="pdf",
        published_format="html",
    )

    assert pair.preprint.raw_score == 3
    assert pair.published.raw_score == 12
    assert pair.to_record()["published_document_format"] == "html"
    assert pair.indicator_deltas["V2"] == 2


def test_methodology_output_repository_writes_r_ready_tables(tmp_path: Path) -> None:
    workflow = MethodologyScoringWorkflow(_scorer())
    pair = workflow.score_pair(
        manuscript_id="biorxiv:10.1101/example",
        preprint_document={
            "methods": "",
            "results": "The odds ratio was 1.45.",
            "statements": "",
        },
        published_document={
            "methods": "",
            "results": "The odds ratio was 1.45 with 95% CI 1.10-1.90.",
            "statements": "",
        },
        preprint_format="pdf",
        published_format="pdf",
    )

    class FakeStorage(Storage):
        def __init__(self) -> None:
            self.tables: dict[str, pd.DataFrame] = {}

        def load_raw(self, df: pd.DataFrame) -> None:
            pass

        def read_raw(self) -> pd.DataFrame:
            return pd.DataFrame()

        def write_table(self, table_name: str, df: pd.DataFrame) -> None:
            self.tables[table_name] = df.copy()

    storage = FakeStorage()
    repository = StorageMethodologyOutputRepository(storage, _config(tmp_path))

    frames = repository.save([pair])

    assert (tmp_path / f"{PAIR_SCORE_TABLE}.csv").exists()
    assert (tmp_path / f"{EVIDENCE_TABLE}.csv").exists()
    assert set(storage.tables) == {PAIR_SCORE_TABLE, EVIDENCE_TABLE}
    assert frames.pair_scores.loc[0, "PRES"] == 2
    assert "V10_delta" in frames.pair_scores.columns


def test_methodology_output_frames_have_stable_empty_schema() -> None:
    frames = build_methodology_output_frames([])

    assert "PRES" in frames.pair_scores.columns
    assert "V10_delta" in frames.pair_scores.columns
    assert list(frames.evidence_rows.columns) == [
        "manuscript_id",
        "version",
        "document_format",
        "indicator",
        "score",
        "rationale",
        "section",
        "text",
        "pattern",
    ]
