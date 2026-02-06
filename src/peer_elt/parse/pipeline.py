from __future__ import annotations

"""Parsing pipelines for PDFs and web articles.

This module contains orchestration code that wires together parsing services and
text processors into two pipelines:

- :class:`PdfParsingPipeline` for PDF inputs (TEI + layout blocks + features)
- :class:`ArticleParsingPipeline` for HTML article inputs (text + features)

Notes
-----
These pipelines are intentionally thin. They delegate actual parsing and feature
logic to injected service/processor implementations that satisfy the protocols
in :mod:`peer_elt.parse.interfaces`.
"""

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
    """Build section text by concatenating labeled layout blocks.

    Parameters
    ----------
    blocks : Sequence[peer_elt.parse.models.LayoutBlock]
        Layout blocks produced by segmentation. Blocks without a ``section``
        label are ignored.

    Returns
    -------
    Mapping[str, str]
        Mapping of section name to concatenated section text (joined with
        newlines).
    """
    sections: dict[str, list[str]] = defaultdict(list)
    for block in blocks:
        if not block.section:
            continue
        sections[block.section].append(block.text)
    return {section: "\n".join(texts) for section, texts in sections.items()}


class PdfParsingPipeline:
    """Orchestrate PDF parsing using GROBID, OpenParse, spaCy, and sentence-BERT.

    Parameters
    ----------
    grobid : peer_elt.parse.interfaces.GrobidService
        Service used to convert a PDF into TEI XML and structure metadata.
    openparse : peer_elt.parse.interfaces.OpenParseService
        Service used to segment TEI XML into layout-aware blocks.
    spacy_processor : peer_elt.parse.interfaces.SpacyProcessor
        Processor used to compute per-section features.
    sentence_bert_processor : peer_elt.parse.interfaces.SentenceBertProcessor
        Processor used to embed per-section text.

    Notes
    -----
    The pipeline assumes the provided services follow the protocol contracts and
    does not perform schema validation beyond assembling outputs.
    """

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
        """Parse a PDF into structured text, features, and embeddings.

        Parameters
        ----------
        pdf_path : pathlib.Path
            Path to the input PDF.

        Returns
        -------
        peer_elt.parse.models.ParsedDocument
            Parsed document bundle including TEI output, layout blocks, sections,
            features, and embeddings.
        """
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
    """Orchestrate HTML scraping with spaCy features and sentence-BERT embeddings.

    Parameters
    ----------
    scraper : peer_elt.parse.interfaces.ArticleScraper
        Service used to fetch article HTML and extract main text.
    spacy_processor : peer_elt.parse.interfaces.SpacyProcessor
        Processor used to compute per-text-bucket features.
    sentence_bert_processor : peer_elt.parse.interfaces.SentenceBertProcessor
        Processor used to embed extracted text.
    """

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
        """Fetch and parse an article URL into text, features, and embeddings.

        Parameters
        ----------
        url : str
            Article URL.

        Returns
        -------
        peer_elt.parse.models.ArticleDocument
            Scraped document bundle including HTML, extracted text, features, and
            embeddings.
        """
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
