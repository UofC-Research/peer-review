from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import pytest

from peer_elt.parse.models import GrobidResult, LayoutBlock, ParsedDocument
from peer_elt.parse.pipeline import PdfParsingPipeline
from peer_elt.parse.processors import SimpleTokenStatsProcessor


@dataclass
class FakeGrobid:
    result: GrobidResult
    seen: Path | None = None

    def pdf_to_tei(self, pdf_path: Path) -> GrobidResult:
        self.seen = pdf_path
        return self.result


@dataclass
class FakeOpenParse:
    blocks: Sequence[LayoutBlock]
    seen_tei: str | None = None
    seen_sections: Mapping[str, Sequence[str]] | None = None

    def segment_layout(
        self,
        tei_xml: str,
        section_hierarchy: Mapping[str, Sequence[str]],
    ) -> Sequence[LayoutBlock]:
        self.seen_tei = tei_xml
        self.seen_sections = section_hierarchy
        return self.blocks


@dataclass
class FakeSpacy:
    features: Mapping[str, Mapping[str, int]]
    seen: Mapping[str, str] | None = None

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        self.seen = sections
        return self.features


@dataclass
class FakeSentenceBert:
    embeddings: Mapping[str, list[float]]
    seen: Mapping[str, str] | None = None

    def embed_sections(self, sections: Mapping[str, str]) -> Mapping[str, list[float]]:
        self.seen = sections
        return self.embeddings


def test_pdf_parsing_pipeline_composes_services(tmp_path: Path) -> None:
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
    processor = SimpleTokenStatsProcessor()

    result = processor.process_sections({"methods": text})

    assert result["methods"]["token_count"] == expected_tokens
    assert result["methods"]["sentence_count"] == expected_sentences
