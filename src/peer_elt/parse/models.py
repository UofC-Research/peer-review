from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class GrobidResult:
    """Container for Grobid structure and bibliography output."""

    tei_xml: str
    bibliography_xml: str | None
    section_hierarchy: Mapping[str, Sequence[str]]


@dataclass(frozen=True)
class LayoutBlock:
    """Layout-aware block with page mapping."""

    text: str
    page: int
    section: str | None = None


@dataclass(frozen=True)
class ParsedDocument:
    """Container for parsed PDF output."""

    source_path: Path
    grobid: GrobidResult
    blocks: Sequence[LayoutBlock]
    sections: Mapping[str, str]
    features: Mapping[str, Mapping[str, int]]
    embeddings: Mapping[str, list[float]]


@dataclass(frozen=True)
class ArticleDocument:
    """Container for scraped article output."""

    source_url: str
    html: str
    text: str
    features: Mapping[str, Mapping[str, int]]
    embeddings: Mapping[str, list[float]]
