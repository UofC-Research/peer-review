from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from peer_elt.parse.interfaces import (
    ArticleScraper,
    GrobidService,
    OpenParseService,
    SentenceBertProcessor,
    SpacyProcessor,
)
from peer_elt.parse.models import ArticleDocument, LayoutBlock, ParsedDocument


def _build_sections(blocks: Sequence[LayoutBlock]) -> Mapping[str, str]:
    sections: dict[str, list[str]] = defaultdict(list)
    for block in blocks:
        if not block.section:
            continue
        sections[block.section].append(block.text)
    return {section: "\n".join(texts) for section, texts in sections.items()}


class PdfParsingPipeline:
    """Orchestrates PDF parsing using Grobid, OpenParse, spaCy, and sentence-BERT."""

    def __init__(
        self,
        grobid: GrobidService,
        openparse: OpenParseService,
        spacy_processor: SpacyProcessor,
        sentence_bert_processor: SentenceBertProcessor,
    ) -> None:
        self._grobid = grobid
        self._openparse = openparse
        self._spacy_processor = spacy_processor
        self._sentence_bert_processor = sentence_bert_processor

    def parse(self, pdf_path: Path) -> ParsedDocument:
        grobid_result = self._grobid.pdf_to_tei(pdf_path)
        blocks = self._openparse.segment_layout(
            grobid_result.tei_xml,
            grobid_result.section_hierarchy,
        )
        sections = _build_sections(blocks)
        features = self._spacy_processor.process_sections(sections)
        embeddings = self._sentence_bert_processor.embed_sections(sections)
        return ParsedDocument(
            source_path=pdf_path,
            grobid=grobid_result,
            blocks=blocks,
            sections=sections,
            features=features,
            embeddings=embeddings,
        )


class ArticleParsingPipeline:
    """Orchestrates web scraping with spaCy and sentence-BERT embeddings."""

    def __init__(
        self,
        scraper: ArticleScraper,
        spacy_processor: SpacyProcessor,
        sentence_bert_processor: SentenceBertProcessor,
    ) -> None:
        self._scraper = scraper
        self._spacy_processor = spacy_processor
        self._sentence_bert_processor = sentence_bert_processor

    def parse(self, url: str) -> ArticleDocument:
        html = self._scraper.fetch_article(url)
        text = self._scraper.extract_text(html)
        sections = {"article": text}
        features = self._spacy_processor.process_sections(sections)
        embeddings = self._sentence_bert_processor.embed_sections(sections)
        return ArticleDocument(
            source_url=url,
            html=html,
            text=text,
            features=features,
            embeddings=embeddings,
        )


__all__ = [
    "ArticleDocument",
    "ArticleParsingPipeline",
    "LayoutBlock",
    "ParsedDocument",
    "PdfParsingPipeline",
]
