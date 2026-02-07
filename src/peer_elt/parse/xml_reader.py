from __future__ import annotations

"""XML readers and extractors for spaCy-ready section text.

This module provides a small XML reading abstraction that turns XML documents
into ``Mapping[str, str]`` payloads that can be fed into ``SpacyProcessor``
implementations. The design uses the Strategy pattern to allow multiple XML
flavors (e.g., TEI vs. custom section tags) and a simple Factory for
constructing readers by format name.
"""

from dataclasses import dataclass, field
from typing import Mapping, Protocol
from xml.etree import ElementTree


class XmlSectionExtractor(Protocol):
    """Strategy interface for extracting section text from XML."""

    def extract_sections(self, root: ElementTree.Element) -> Mapping[str, str]:
        """Extract section text from an XML root."""


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


@dataclass(frozen=True)
class SectionTagExtractor(XmlSectionExtractor):
    """Extract sections from XML using a dedicated section tag.

    Parameters
    ----------
    section_tag : str, default="section"
        Tag name to treat as a section container.
    name_attribute : str, default="name"
        Attribute name that stores the section label.
    """

    section_tag: str = "section"
    name_attribute: str = "name"

    def extract_sections(self, root: ElementTree.Element) -> Mapping[str, str]:
        sections: dict[str, str] = {}
        for section in root.iter(self.section_tag):
            name = section.attrib.get(self.name_attribute)
            if not name:
                continue
            text = _collapse_whitespace(" ".join(section.itertext()))
            if text:
                sections[name] = text
        return sections


@dataclass(frozen=True)
class TeiSectionExtractor(XmlSectionExtractor):
    """Extract sections from TEI-like XML.

    This implementation uses ``div`` elements as section containers. It
    prefers the ``type`` attribute as a section name and falls back to a
    ``head`` element if present.
    """

    div_tag: str = "div"
    type_attribute: str = "type"
    head_tag: str = "head"

    def extract_sections(self, root: ElementTree.Element) -> Mapping[str, str]:
        sections: dict[str, str] = {}
        for div in root.iter(self.div_tag):
            name = div.attrib.get(self.type_attribute)
            if not name:
                head = div.find(self.head_tag)
                if head is not None:
                    name = _collapse_whitespace(" ".join(head.itertext()))
            if not name:
                continue
            text = _collapse_whitespace(" ".join(div.itertext()))
            if text:
                sections[name] = text
        return sections


@dataclass(frozen=True)
class XmlSectionReader:
    """Parse XML text into spaCy-ready section mappings."""

    extractor: XmlSectionExtractor

    def read(self, xml: str) -> Mapping[str, str]:
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as exc:
            raise ValueError("Invalid XML payload.") from exc
        return self.extractor.extract_sections(root)


@dataclass(frozen=True)
class XmlSectionReaderFactory:
    """Factory for creating XML readers by format name."""

    registry: Mapping[str, XmlSectionExtractor] = field(
        default_factory=lambda: {
            "section-tag": SectionTagExtractor(),
            "tei": TeiSectionExtractor(),
        }
    )

    def create(self, format_name: str) -> XmlSectionReader:
        try:
            extractor = self.registry[format_name]
        except KeyError as exc:
            raise ValueError(f"Unknown XML format: {format_name}") from exc
        return XmlSectionReader(extractor=extractor)


__all__ = [
    "SectionTagExtractor",
    "TeiSectionExtractor",
    "XmlSectionExtractor",
    "XmlSectionReader",
    "XmlSectionReaderFactory",
]
