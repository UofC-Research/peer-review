from __future__ import annotations

from pathlib import Path

import pytest

from peer_elt.acquire.corpus import MatchedManuscriptPair, PairAcquisitionResult
from peer_elt.acquire.full_text import AcquisitionResult
from peer_elt.parse.processors import SimpleTokenStatsProcessor
from peer_elt.parse.xml_reader import SectionTagExtractor, XmlSectionReader
from peer_elt.transform.artifacts import (
    AcquiredArtifactScoringWorkflow,
    ArtifactParserRegistry,
    HtmlArtifactParser,
    PlainTextHtmlExtractor,
    XmlArtifactParser,
)
from peer_elt.transform.methodology import MethodologyScoringWorkflow
from peer_elt.transform.scoring import (
    HybridScorer,
    RuleBasedScorer,
    default_rule_patterns,
)


def _scoring_workflow() -> MethodologyScoringWorkflow:
    return MethodologyScoringWorkflow(
        HybridScorer(RuleBasedScorer(default_rule_patterns()))
    )


def _pair() -> MatchedManuscriptPair:
    return MatchedManuscriptPair(
        manuscript_id="biorxiv:10.1101/example",
        server="biorxiv",
        preprint_doi="10.1101/example",
        preprint_version="1",
        preprint_date="2020-01-01",
        published_doi="10.7554/example",
    )


def _success(doc_id: str, fmt: str, path: Path) -> AcquisitionResult:
    return AcquisitionResult(
        doc_id=doc_id,
        success=True,
        format=fmt,  # type: ignore[arg-type]
        url=f"https://example.org/{doc_id}",
        path=path,
        needs_human_confirmation=False,
    )


def test_acquired_xml_artifacts_are_parsed_and_scored(tmp_path: Path) -> None:
    """Score acquired XML artifacts through parser strategies and workflow facade."""
    preprint_path = tmp_path / "preprint.xml"
    published_path = tmp_path / "published.xml"
    preprint_path.write_text(
        """
        <document>
          <section name="methods">We used a regression model.</section>
          <section name="results">The odds ratio was 1.45.</section>
        </document>
        """,
        encoding="utf-8",
    )
    published_path.write_text(
        """
        <document>
          <section name="methods">
            We used a regression model adjusted for covariate A.
            A power calculation assumed alpha 0.05 and effect size 0.4.
          </section>
          <section name="results">
            The odds ratio was 1.45 with 95% CI 1.10-1.90, p = 0.02.
          </section>
          <section name="statements">Data availability is provided on GitHub.</section>
        </document>
        """,
        encoding="utf-8",
    )
    registry = ArtifactParserRegistry(
        {
            "xml": XmlArtifactParser(
                XmlSectionReader(extractor=SectionTagExtractor())
            )
        }
    )
    workflow = AcquiredArtifactScoringWorkflow(registry, _scoring_workflow())

    pair = workflow.score(
        PairAcquisitionResult(
            pair=_pair(),
            preprint=_success("preprint", "xml", preprint_path),
            published=_success("published", "xml", published_path),
        )
    )

    assert pair.preprint.raw_score == 3
    assert pair.published.raw_score == 12
    assert pair.pres == 9
    assert pair.to_record()["preprint_document_format"] == "xml"
    assert pair.to_record()["published_document_format"] == "xml"


def test_acquired_html_artifact_parser_builds_article_document(tmp_path: Path) -> None:
    """Parse a local HTML artifact without network access."""
    html_path = tmp_path / "article.html"
    html_path.write_text(
        """
        <html>
          <body>
            <h2>Methods</h2>
            <p>We used a regression model.</p>
            <script>ignored()</script>
            <h2>Results</h2>
            <p>The odds ratio was 1.45.</p>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    parser = HtmlArtifactParser(
        text_extractor=PlainTextHtmlExtractor(),
        spacy_processor=SimpleTokenStatsProcessor(),
    )

    parsed = parser.parse(_success("article", "html", html_path))

    assert parsed.format == "html"
    assert "ignored" not in parsed.document.text
    assert "Methods" in parsed.document.text
    assert parsed.document.features["article"]["token_count"] > 0


def test_artifact_registry_rejects_missing_parser(tmp_path: Path) -> None:
    """Raise a clear error when no strategy exists for an acquired format."""
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF")
    registry = ArtifactParserRegistry({})

    with pytest.raises(ValueError, match="No artifact parser registered"):
        registry.parse(_success("paper", "pdf", path))


def test_artifact_parser_rejects_failed_acquisition(tmp_path: Path) -> None:
    """Do not parse acquisition failures as valid scoring inputs."""
    registry = ArtifactParserRegistry(
        {"xml": XmlArtifactParser(XmlSectionReader(extractor=SectionTagExtractor()))}
    )
    failed = AcquisitionResult(
        doc_id="missing",
        success=False,
        format="xml",
        url=None,
        path=None,
        needs_human_confirmation=True,
        error_message="not found",
    )

    with pytest.raises(ValueError, match="Cannot parse failed acquisition"):
        registry.parse(failed)
