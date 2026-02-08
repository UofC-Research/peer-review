from __future__ import annotations

"""Tests for XML section reading.

These tests verify that XML payloads can be parsed into a section mapping
(`dict[str, str]`) suitable for downstream spaCy-style processing.

Covered behaviors:
- extracting named sections from a custom `<section name="...">` format,
- extracting sections from TEI-like `<div>` elements using `type` or `head`,
- selecting extractors via the reader factory, and
- raising a helpful error for invalid XML input.
"""

import pytest

from peer_elt.parse.xml_reader import (
    SectionTagExtractor,
    TeiSectionExtractor,
    XmlSectionReader,
    XmlSectionReaderFactory,
)


def test_section_tag_reader_extracts_named_sections() -> None:
    """Extract named sections from `<section name="...">` containers."""
    xml = """
    <document>
        <section name="methods"><p>Some methods.</p></section>
        <section name="results"><p>Good results.</p></section>
    </document>
    """

    reader = XmlSectionReader(extractor=SectionTagExtractor())

    assert reader.read(xml) == {
        "methods": "Some methods.",
        "results": "Good results.",
    }


def test_tei_reader_prefers_type_attribute_and_falls_back_to_head() -> None:
    """Prefer `div@type` and fall back to `div/head` when extracting section names."""
    xml = """
    <TEI>
        <text>
            <body>
                <div type="methods"><p>First.</p><p>Second.</p></div>
                <div><head>Conclusion</head><p>Done.</p></div>
            </body>
        </text>
    </TEI>
    """

    reader = XmlSectionReader(extractor=TeiSectionExtractor())

    assert reader.read(xml) == {
        "methods": "First. Second.",
        "Conclusion": "Conclusion Done.",
    }


def test_reader_factory_handles_formats_and_rejects_unknown() -> None:
    """Create known readers and reject unknown format names."""
    factory = XmlSectionReaderFactory()

    reader = factory.create("tei")

    assert isinstance(reader.extractor, TeiSectionExtractor)
    with pytest.raises(ValueError, match="Unknown XML format"):
        factory.create("unknown-format")


def test_reader_raises_on_invalid_xml() -> None:
    """Raise ValueError when given an invalid XML payload."""
    reader = XmlSectionReader(extractor=SectionTagExtractor())

    with pytest.raises(ValueError, match="Invalid XML"):
        reader.read("<document><section>")
