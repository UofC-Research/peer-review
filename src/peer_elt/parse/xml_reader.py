from __future__ import annotations

"""XML readers and extractors for spaCy-ready section text.

This module provides a small XML reading abstraction that turns XML documents
into ``Mapping[str, str]`` payloads that can be fed into
:class:`peer_elt.parse.interfaces.SpacyProcessor` implementations.

The design uses:
- a Strategy interface (:class:`XmlSectionExtractor`) for supporting multiple XML
  "flavors" (e.g., TEI vs. custom section tags), and
- a small factory (:class:`XmlSectionReaderFactory`) for constructing readers by
  format name.
"""

from dataclasses import dataclass, field
from typing import Mapping, Protocol
from xml.etree import ElementTree


class XmlSectionExtractor(Protocol):
    """Strategy interface for extracting section text from an XML document."""

    def extract_sections(self, root: ElementTree.Element) -> Mapping[str, str]:
        """Extract section text from an XML root element.

        Parameters
        ----------
        root : xml.etree.ElementTree.Element
            Parsed XML root element.

        Returns
        -------
        Mapping[str, str]
            Mapping of section name to extracted section text.
        """


def _collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace into single spaces.

    Parameters
    ----------
    text : str
        Input text.

    Returns
    -------
    str
        Normalized text with collapsed whitespace.
    """
    return " ".join(text.split())


@dataclass(frozen=True)
class SectionTagExtractor(XmlSectionExtractor):
    """Extract sections from XML using a dedicated section tag.

    This extractor assumes the XML contains repeated "section container"
    elements, each with an attribute storing the section label.

    Attributes
    ----------
    section_tag : str
        Tag name to treat as a section container.
    name_attribute : str
        Attribute name that stores the section label.
    """

    section_tag: str = "section"
    name_attribute: str = "name"

    def extract_sections(self, root: ElementTree.Element) -> Mapping[str, str]:
        """Extract sections based on container tags and a name attribute.

        Parameters
        ----------
        root : xml.etree.ElementTree.Element
            Parsed XML root element.

        Returns
        -------
        Mapping[str, str]
            Mapping of section label to extracted section text.

        Notes
        -----
        - Sections without a name attribute are ignored.
        - If multiple sections have the same name, later sections overwrite
          earlier ones.
        """
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

    This extractor treats ``div`` elements as section containers. It prefers the
    ``type`` attribute as a section name and falls back to the text of a ``head``
    element if present.

    Attributes
    ----------
    div_tag : str
        Tag name treated as a section container (commonly ``"div"``).
    type_attribute : str
        Attribute name used as a section label (commonly ``"type"``).
    head_tag : str
        Tag name for the heading element (commonly ``"head"``).

    Notes
    -----
    This implementation does not currently perform namespace-aware searches.
    If your TEI uses namespaces (e.g., ``{http://www.tei-c.org/ns/1.0}div``),
    consider enhancing this extractor to match on local names.
    """

    div_tag: str = "div"
    type_attribute: str = "type"
    head_tag: str = "head"

    def extract_sections(self, root: ElementTree.Element) -> Mapping[str, str]:
        """Extract TEI-like sections using ``div`` + (``type`` or ``head``).

        Parameters
        ----------
        root : xml.etree.ElementTree.Element
            Parsed XML root element.

        Returns
        -------
        Mapping[str, str]
            Mapping of section name to extracted section text.

        Notes
        -----
        - ``div.itertext()`` includes the heading text as well as body text.
        - If multiple sections have the same inferred name, later sections
          overwrite earlier ones.
        """


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
