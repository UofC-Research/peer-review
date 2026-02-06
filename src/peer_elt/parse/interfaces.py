from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol, Sequence

from peer_elt.parse.models import GrobidResult, LayoutBlock


class GrobidService(Protocol):
    """Strategy interface for turning PDFs into TEI XML plus structure metadata."""

    def pdf_to_tei(self, pdf_path: Path) -> GrobidResult:
        """Return the TEI XML and structure metadata for a PDF."""


class OpenParseService(Protocol):
    """Strategy interface for converting TEI XML into layout-aware blocks."""

    def segment_layout(
        self,
        tei_xml: str,
        section_hierarchy: Mapping[str, Sequence[str]],
    ) -> Sequence[LayoutBlock]:
        """Return layout blocks with page mapping."""


class ArticleScraper(Protocol):
    """Strategy interface for scraping article HTML and extracting text."""

    def fetch_article(self, url: str) -> str:
        """Return raw HTML for an article URL."""

    def extract_text(self, html: str) -> str:
        """Return the main article text from raw HTML."""


class SpacyProcessor(Protocol):
    """Strategy interface for deriving features from sections."""

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        """Return per-section features."""


class SentenceBertProcessor(Protocol):
    """Strategy interface for embedding sections with sentence-BERT."""

    def embed_sections(self, sections: Mapping[str, str]) -> Mapping[str, list[float]]:
        """Return per-section embeddings."""
