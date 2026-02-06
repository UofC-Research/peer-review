from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class GrobidResult:
    """Container for GROBID structure and bibliography output.

    Attributes
    ----------
    tei_xml : str
        TEI XML returned by GROBID.
    bibliography_xml : str | None
        Optional bibliography XML (if produced by the service).
    section_hierarchy : Mapping[str, Sequence[str]]
        Section hierarchy metadata used to guide downstream segmentation.
    """

    tei_xml: str
    bibliography_xml: str | None
    section_hierarchy: Mapping[str, Sequence[str]]


@dataclass(frozen=True)
class LayoutBlock:
    """Layout-aware text block with page mapping.

    Attributes
    ----------
    text : str
        Block text content.
    page : int
        1-based page number where the block appears.
    section : str | None, default=None
        Optional section label assigned during segmentation.
    """

    text: str
    page: int
    section: str | None = None


@dataclass(frozen=True)
class ParsedDocument:
    """Parsed PDF document container.

    Attributes
    ----------
    source_path : pathlib.Path
        Path to the source PDF.
    grobid : GrobidResult
        TEI XML and extracted structure metadata.
    blocks : Sequence[LayoutBlock]
        Layout-aware blocks produced by segmentation.
    sections : Mapping[str, str]
        Mapping of section name to extracted section text.
    features : Mapping[str, Mapping[str, int]]
        Mapping of section name to extracted integer-valued features.
    embeddings : Mapping[str, list[float]]
        Mapping of section name to embedding vector.
    """

    source_path: Path
    grobid: GrobidResult
    blocks: Sequence[LayoutBlock]
    sections: Mapping[str, str]
    features: Mapping[str, Mapping[str, int]]
    embeddings: Mapping[str, list[float]]


@dataclass(frozen=True)
class ArticleDocument:
    """Scraped article document container.

    Attributes
    ----------
    source_url : str
        URL of the scraped article.
    html : str
        Raw HTML fetched from the source URL.
    text : str
        Extracted main article text.
    features : Mapping[str, Mapping[str, int]]
        Mapping of section name (or logical text bucket) to extracted
        integer-valued features.
    embeddings : Mapping[str, list[float]]
        Mapping of section name (or logical text bucket) to embedding vector.
    """

    source_url: str
    html: str
    text: str
    features: Mapping[str, Mapping[str, int]]
    embeddings: Mapping[str, list[float]]
