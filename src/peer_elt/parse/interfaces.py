from __future__ import annotations

"""Protocol interfaces for the parsing subsystem.

This module defines structural service contracts (via ``typing.Protocol``) used
by the parsing pipeline. These protocols allow dependency injection of concrete
implementations (e.g., wrappers around external services) without requiring
inheritance.

Notes
-----
- Protocols are *structural*: any object with the required methods is accepted.
- The protocols here are intentionally small and focused on I/O boundaries.
"""

from pathlib import Path
from typing import Mapping, Protocol, Sequence

from peer_elt.parse.models import GrobidResult, LayoutBlock


class GrobidService(Protocol):
    """Service interface for converting PDFs into TEI XML plus structure metadata."""

    def pdf_to_tei(self, pdf_path: Path) -> GrobidResult:
        """Convert a PDF to TEI XML.

        Parameters
        ----------
        pdf_path : pathlib.Path
            Path to the input PDF.

        Returns
        -------
        peer_elt.parse.models.GrobidResult
            TEI XML plus extracted structure metadata.
        """


class OpenParseService(Protocol):
    """Service interface for converting TEI XML into layout-aware blocks."""

    def segment_layout(
        self,
        tei_xml: str,
        section_hierarchy: Mapping[str, Sequence[str]],
    ) -> Sequence[LayoutBlock]:
        """Segment TEI XML into layout-aware blocks.

        Parameters
        ----------
        tei_xml : str
            TEI XML document as a string.
        section_hierarchy : Mapping[str, Sequence[str]]
            Mapping defining section names and their allowed subsection headings
            used to guide segmentation.

        Returns
        -------
        Sequence[peer_elt.parse.models.LayoutBlock]
            Layout-aware blocks, typically including page mapping information.
        """


class ArticleScraper(Protocol):
    """Service interface for fetching article HTML and extracting main text."""

    def fetch_article(self, url: str) -> str:
        """Fetch raw HTML for an article URL.

        Parameters
        ----------
        url : str
            Article URL.

        Returns
        -------
        str
            Raw HTML content.
        """

    def extract_text(self, html: str) -> str:
        """Extract the main article text from raw HTML.

        Parameters
        ----------
        html : str
            Raw HTML content.

        Returns
        -------
        str
            Extracted main article text.
        """


class SpacyProcessor(Protocol):
    """Service interface for deriving per-section features."""

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        """Compute per-section features from text.

        Parameters
        ----------
        sections : Mapping[str, str]
            Mapping of section name to section text.

        Returns
        -------
        Mapping[str, Mapping[str, int]]
            Mapping of section name to mapping of feature name to integer value.
        """


class SentenceBertProcessor(Protocol):
    """Service interface for embedding sections with sentence-BERT."""

    def embed_sections(self, sections: Mapping[str, str]) -> Mapping[str, list[float]]:
        """Embed section text into vectors.

        Parameters
        ----------
        sections : Mapping[str, str]
            Mapping of section name to section text.

        Returns
        -------
        Mapping[str, list[float]]
            Mapping of section name to embedding vector (as floats).
        """
