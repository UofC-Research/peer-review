from __future__ import annotations

"""Adapters that convert parsed manuscripts into methodology scoring sections.

The scoring rules operate on canonical ``methods``, ``results``, and
``statements`` sections. Parsers and scrapers do not always expose those exact
names, so this module keeps section-normalization policy out of the scoring
workflow.
"""

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Protocol

from peer_elt.parse.models import ArticleDocument, ParsedDocument


CANONICAL_SECTIONS: tuple[str, ...] = ("methods", "results", "statements")

SECTION_ALIASES: Mapping[str, tuple[str, ...]] = {
    "methods": (
        "methods",
        "method",
        "methodology",
        "materials and methods",
        "statistical analysis",
        "statistical methods",
    ),
    "results": (
        "results",
        "findings",
        "outcomes",
    ),
    "statements": (
        "statements",
        "declarations",
        "data availability",
        "code availability",
        "availability",
        "supplementary material",
    ),
}


class SectionAdapter(Protocol):
    """Strategy interface for exposing canonical methodology sections."""

    def to_sections(self, document) -> Mapping[str, str]:
        """Return canonical methodology sections for ``document``.

        Parameters
        ----------
        document
            Parsed document object or section mapping accepted by the adapter.

        Returns
        -------
        Mapping[str, str]
            Mapping with ``methods``, ``results``, and ``statements`` keys.
        """


class SectionMappingAdapter:
    """Normalize parser-provided section mappings to canonical scoring names."""

    def to_sections(self, document: Mapping[str, str]) -> Mapping[str, str]:
        """Return canonical sections from an arbitrary section mapping.

        Parameters
        ----------
        document : Mapping[str, str]
            Section text keyed by parser- or source-specific section names.

        Returns
        -------
        Mapping[str, str]
            Canonical section mapping. Missing canonical sections are emitted
            as empty strings.
        """
        sections: dict[str, list[str]] = defaultdict(list)
        for name, text in document.items():
            canonical = _canonical_section_name(name)
            if canonical and text:
                sections[canonical].append(text)

        return {
            section: "\n".join(sections.get(section, ()))
            for section in CANONICAL_SECTIONS
        }


class ParsedDocumentAdapter:
    """Adapter for PDF/XML parser output.

    Parameters
    ----------
    section_adapter : SectionMappingAdapter | None, default=None
        Mapping adapter used to normalize ``ParsedDocument.sections``.
    """

    def __init__(self, section_adapter: SectionMappingAdapter | None = None) -> None:
        self._section_adapter = section_adapter or SectionMappingAdapter()

    def to_sections(self, document: ParsedDocument) -> Mapping[str, str]:
        """Normalize ``ParsedDocument.sections`` for methodology scoring.

        Parameters
        ----------
        document : peer_elt.parse.models.ParsedDocument
            Parsed PDF/XML document containing section text.

        Returns
        -------
        Mapping[str, str]
            Canonical methodology sections for scoring.
        """
        return self._section_adapter.to_sections(document.sections)


class ArticleDocumentAdapter:
    """Adapter for article scraper output.

    HTML scraping can leave the article as one text blob. When recognizable
    headings are present, those sections are mapped directly. Otherwise, the
    same full text is exposed to each canonical bucket so the conservative
    scorer can still find preregistered cues while downstream review flags
    remain available.

    Parameters
    ----------
    section_adapter : SectionMappingAdapter | None, default=None
        Mapping adapter used after heading-based article section extraction.
    """

    def __init__(self, section_adapter: SectionMappingAdapter | None = None) -> None:
        self._section_adapter = section_adapter or SectionMappingAdapter()

    def to_sections(self, document: ArticleDocument) -> Mapping[str, str]:
        """Return canonical sections from an ``ArticleDocument``.

        Parameters
        ----------
        document : peer_elt.parse.models.ArticleDocument
            Scraped article document containing extracted article text.

        Returns
        -------
        Mapping[str, str]
            Canonical methodology sections for scoring.
        """
        sections = _split_heading_sections(document.text)
        canonical = self._section_adapter.to_sections(sections)
        if any(canonical.values()):
            return canonical
        return {section: document.text for section in CANONICAL_SECTIONS}


class MethodologySectionAdapter:
    """Dispatch adapter for supported parsed document shapes.

    Parameters
    ----------
    mapping_adapter : SectionMappingAdapter | None, default=None
        Adapter used for direct section mappings.
    parsed_adapter : ParsedDocumentAdapter | None, default=None
        Adapter used for ``ParsedDocument`` instances.
    article_adapter : ArticleDocumentAdapter | None, default=None
        Adapter used for ``ArticleDocument`` instances.
    """

    def __init__(
            self,
            mapping_adapter: SectionMappingAdapter | None = None,
            parsed_adapter: ParsedDocumentAdapter | None = None,
            article_adapter: ArticleDocumentAdapter | None = None,
    ) -> None:
        self._mapping_adapter = mapping_adapter or SectionMappingAdapter()
        self._parsed_adapter = parsed_adapter or ParsedDocumentAdapter(
            self._mapping_adapter
        )
        self._article_adapter = article_adapter or ArticleDocumentAdapter(
            self._mapping_adapter
        )

    def to_sections(self, document) -> Mapping[str, str]:
        """Return canonical sections for mappings, parsed PDFs, or articles.

        Parameters
        ----------
        document
            One of ``ParsedDocument``, ``ArticleDocument``, or a section
            ``Mapping[str, str]``.

        Returns
        -------
        Mapping[str, str]
            Canonical methodology sections for scoring.

        Raises
        ------
        TypeError
            If ``document`` has no registered adapter strategy.
        """
        if isinstance(document, ParsedDocument):
            return self._parsed_adapter.to_sections(document)
        if isinstance(document, ArticleDocument):
            return self._article_adapter.to_sections(document)
        if isinstance(document, Mapping):
            return self._mapping_adapter.to_sections(document)
        raise TypeError(f"Unsupported methodology document type: {type(document)!r}")


def _canonical_section_name(name: str) -> str | None:
    """Return the canonical section name for a parser heading.

    Parameters
    ----------
    name : str
        Raw section heading.

    Returns
    -------
    str | None
        Canonical section name, or ``None`` when the heading is not relevant to
        methodology scoring.
    """
    normalized_name = _normalize_heading(name)
    for canonical, aliases in SECTION_ALIASES.items():
        normalized_aliases = {_normalize_heading(alias) for alias in aliases}
        if normalized_name in normalized_aliases:
            return canonical
    return None


def _split_heading_sections(text: str) -> Mapping[str, str]:
    """Split article text into coarse sections using line headings.

    Parameters
    ----------
    text : str
        Extracted article text.

    Returns
    -------
    Mapping[str, str]
        Recognized canonical sections keyed by section name.
    """
    sections: dict[str, list[str]] = defaultdict(list)
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _canonical_section_name(line)
        if heading:
            current = heading
            continue
        if current:
            sections[current].append(line)
    return {name: "\n".join(lines) for name, lines in sections.items()}


def _normalize_heading(value: str) -> str:
    """Normalize a heading for alias matching.

    Parameters
    ----------
    value : str
        Raw heading text.

    Returns
    -------
    str
        Lowercase, whitespace-normalized heading containing only alphanumeric
        tokens.
    """
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(normalized.split())


__all__ = [
    "ArticleDocumentAdapter",
    "CANONICAL_SECTIONS",
    "MethodologySectionAdapter",
    "ParsedDocumentAdapter",
    "SectionAdapter",
    "SectionMappingAdapter",
]
