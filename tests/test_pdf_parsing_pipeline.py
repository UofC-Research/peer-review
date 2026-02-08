from __future__ import annotations

"""Tests for the PDF parsing pipeline.

These tests verify that `PdfParsingPipeline` correctly orchestrates its injected
dependencies (GROBID, layout segmentation, feature extraction, embeddings) and
that the lightweight token statistics processor behaves deterministically.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pytest

from peer_elt.parse.models import GrobidResult, LayoutBlock, ParsedDocument
from peer_elt.parse.pipeline import PdfParsingPipeline
from peer_elt.parse.processors import SimpleTokenStatsProcessor


@dataclass
class FakeGrobid:
    """Fake GROBID service returning a predefined `GrobidResult`."""

    result: GrobidResult
    seen: Path | None = None

    def pdf_to_tei(self, pdf_path: Path) -> GrobidResult:
        """Record the PDF path and return the predefined result.

        Args:
            pdf_path: Path to the input PDF.

        Returns:
            The predefined `GrobidResult`.
        """
        self.seen = pdf_path
        return self.result


@dataclass
class FakeOpenParse:
    """Fake OpenParse service returning predefined layout blocks."""

    blocks: Sequence[LayoutBlock]
    seen_tei: str | None = None
    seen_sections: Mapping[str, Sequence[str]] | None = None

    def segment_layout(
        self,
        tei_xml: str,
        section_hierarchy: Mapping[str, Sequence[str]],
    ) -> Sequence[LayoutBlock]:
        """Record TEI inputs and return predefined blocks.

        Args:
            tei_xml: TEI XML string.
            section_hierarchy: Section hierarchy mapping used for segmentation.

        Returns:
            A predefined sequence of `LayoutBlock` instances.
        """
        self.seen_tei = tei_xml
        self.seen_sections = section_hierarchy
        return self.blocks


@dataclass
class FakeSpacy:
    """Fake feature extractor capturing the sections it receives."""

    features: Mapping[str, Mapping[str, int]]
    seen: Mapping[str, str] | None = None

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        """Record sections and return predefined features.

        Args:
            sections: Mapping of section name to section text.

        Returns:
            Predefined feature mapping.
        """
        self.seen = sections
        return self.features


@dataclass
class FakeSentenceBert:
    """Fake embedding processor capturing the sections it receives."""

    embeddings: Mapping[str, list[float]]
    seen: Mapping[str, str] | None = None

    def embed_sections(self, sections: Mapping[str, str]) -> Mapping[str, list[float]]:
        """Record sections and return predefined embeddings.

        Args:
            sections: Mapping of section name to section text.

        Returns:
            Predefined embedding mapping.
        """
        self.seen = sections
        return self.embeddings


def test_pdf_parsing_pipeline_composes_services(tmp_path: Path) -> None:
    """Compose parsing services and produce a `ParsedDocument`.

    Args:
        tmp_path: Pytest fixture providing a temporary directory.

    Asserts:
        The pipeline passes expected inputs between services and returns a
        `ParsedDocument` matching the assembled outputs.
    """
    pdf_path = tmp_path / "example.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    grobid_result = GrobidResult(
        tei_xml="<tei>mock</tei>",
        bibliography_xml="<biblio>mock</biblio>",
        section_hierarchy={"methods": ["methods"]},
    )
    blocks = [LayoutBlock(text="Some methods.", page=1, section="methods")]
    grobid = FakeGrobid(result=grobid_result)
    openparse = FakeOpenParse(blocks=blocks)
    spacy = FakeSpacy(features={"methods": {"token_count": 2, "sentence_count": 1}})
    sbert = FakeSentenceBert(embeddings={"methods": [0.1, 0.2]})

    pipeline = PdfParsingPipeline(
        grobid=grobid,
        openparse=openparse,
        spacy_processor=spacy,
        sentence_bert_processor=sbert,
    )
    parsed = pipeline.parse(pdf_path)

    assert grobid.seen == pdf_path
    assert openparse.seen_tei == "<tei>mock</tei>"
    assert openparse.seen_sections == {"methods": ["methods"]}
    assert spacy.seen == {"methods": "Some methods."}
    assert sbert.seen == {"methods": "Some methods."}
    assert parsed == ParsedDocument(
        source_path=pdf_path,
        grobid=grobid_result,
        blocks=blocks,
        sections={"methods": "Some methods."},
        features={"methods": {"token_count": 2, "sentence_count": 1}},
        embeddings={"methods": [0.1, 0.2]},
    )


@pytest.mark.parametrize(
    ("text", "expected_tokens", "expected_sentences"),
    [
        ("", 0, 0),
        ("One sentence.", 2, 1),
        ("Two sentences! Another one?", 4, 2),
    ],
)
def test_simple_token_stats_processor_counts(text: str, expected_tokens: int, expected_sentences: int) -> None:
    """Count tokens and sentence-like spans for a section.

    Args:
        text: Input section text.
        expected_tokens: Expected whitespace-token count.
        expected_sentences: Expected sentence-like span count.
    """
    processor = SimpleTokenStatsProcessor()

    result = processor.process_sections({"methods": text})

    assert result["methods"]["token_count"] == expected_tokens
    assert result["methods"]["sentence_count"] == expected_sentences
