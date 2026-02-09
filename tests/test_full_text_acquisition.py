from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from peer_elt.acquire.full_text import (
    AcquisitionRequest,
    acquire_full_text,
    acquire_full_text_pair,
)


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    content: bytes = b""
    headers: Mapping[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", self.headers or {})


def test_acquire_prefers_pdf_then_stops_on_success(tmp_path: Path) -> None:
    calls: list[str] = []

    def http_get(url: str, timeout: float) -> FakeResponse:
        calls.append(url)
        if url.endswith(".pdf"):
            return FakeResponse(
                status_code=200,
                content=b"%PDF-1.4 fake pdf bytes",
                headers={"content-type": "application/pdf"},
            )
        return FakeResponse(status_code=404)

    req = AcquisitionRequest(
        doc_id="doc-1",
        pdf_url="https://example.org/paper.pdf",
        xml_url="https://example.org/paper.xml",
        html_url="https://example.org/paper.html",
    )

    result = acquire_full_text(req, base_dir=tmp_path, http_get=http_get)

    assert result.success is True
    assert result.format == "pdf"
    assert result.needs_human_confirmation is False
    assert result.path is not None
    assert result.path.exists()
    assert calls == [
        "https://example.org/paper.pdf",
    ]


def test_acquire_falls_back_pdf_to_xml(tmp_path: Path) -> None:
    calls: list[str] = []

    def http_get(url: str, timeout: float) -> FakeResponse:
        calls.append(url)
        if url.endswith(".pdf"):
            return FakeResponse(status_code=404)
        if url.endswith(".xml"):
            return FakeResponse(
                status_code=200,
                content=b"<article><title>ok</title></article>",
                headers={"content-type": "application/xml"},
            )
        return FakeResponse(status_code=404)

    req = AcquisitionRequest(
        doc_id="doc-2",
        pdf_url="https://example.org/paper.pdf",
        xml_url="https://example.org/paper.xml",
        html_url="https://example.org/paper.html",
    )

    result = acquire_full_text(req, base_dir=tmp_path, http_get=http_get)

    assert result.success is True
    assert result.format == "xml"
    assert result.path is not None
    assert result.path.suffix == ".xml"
    assert calls == [
        "https://example.org/paper.pdf",
        "https://example.org/paper.xml",
    ]


def test_acquire_falls_back_pdf_to_xml_to_html(tmp_path: Path) -> None:
    calls: list[str] = []

    def http_get(url: str, timeout: float) -> FakeResponse:
        calls.append(url)
        if url.endswith(".html"):
            return FakeResponse(
                status_code=200,
                content=b"<html><body>ok</body></html>",
                headers={"content-type": "text/html"},
            )
        return FakeResponse(status_code=500)

    req = AcquisitionRequest(
        doc_id="doc-3",
        pdf_url="https://example.org/paper.pdf",
        xml_url="https://example.org/paper.xml",
        html_url="https://example.org/paper.html",
    )

    result = acquire_full_text(req, base_dir=tmp_path, http_get=http_get)

    assert result.success is True
    assert result.format == "html"
    assert result.path is not None
    assert result.path.suffix == ".html"
    assert calls == [
        "https://example.org/paper.pdf",
        "https://example.org/paper.xml",
        "https://example.org/paper.html",
    ]


def test_acquire_flags_for_human_when_all_fail(tmp_path: Path) -> None:
    def http_get(url: str, timeout: float) -> FakeResponse:
        return FakeResponse(status_code=404)

    req = AcquisitionRequest(
        doc_id="doc-4",
        pdf_url="https://example.org/paper.pdf",
        xml_url="https://example.org/paper.xml",
        html_url="https://example.org/paper.html",
    )

    result = acquire_full_text(req, base_dir=tmp_path, http_get=http_get)

    assert result.success is False
    assert result.format is None
    assert result.path is None
    assert result.needs_human_confirmation is True
    assert "All retrieval attempts failed" in (result.error_message or "")


def test_acquire_flags_for_human_when_no_urls_exist(tmp_path: Path) -> None:
    calls: list[str] = []

    def http_get(url: str, timeout: float) -> FakeResponse:
        calls.append(url)
        return FakeResponse(status_code=200, content=b"should not be called")

    req = AcquisitionRequest(
        doc_id="doc-no-urls",
        pdf_url=None,
        xml_url=None,
        html_url=None,
    )

    result = acquire_full_text(req, base_dir=tmp_path, http_get=http_get)

    assert result.success is False
    assert result.format is None
    assert result.path is None
    assert result.needs_human_confirmation is True
    assert "All retrieval attempts failed" in (result.error_message or "")
    assert calls == []


def test_pair_acquisition_matches_html_when_published_only_has_html(tmp_path: Path) -> None:
    calls: list[str] = []

    def http_get(url: str, timeout: float) -> FakeResponse:
        calls.append(url)
        # Always succeed for whatever is requested so we can inspect *order*
        if url.endswith(".html"):
            return FakeResponse(status_code=200, content=b"<html>ok</html>")
        if url.endswith(".pdf"):
            return FakeResponse(status_code=200, content=b"%PDF ok")
        if url.endswith(".xml"):
            return FakeResponse(status_code=200, content=b"<xml>ok</xml>")
        return FakeResponse(status_code=404)

    preprint = AcquisitionRequest(
        doc_id="pre-1",
        pdf_url="https://example.org/preprint.pdf",
        xml_url="https://example.org/preprint.xml",
        html_url="https://example.org/preprint.html",
    )
    published = AcquisitionRequest(
        doc_id="pub-1",
        pdf_url=None,
        xml_url=None,
        html_url="https://example.org/published.html",
    )

    pre_res, pub_res = acquire_full_text_pair(
        preprint=preprint,
        published=published,
        base_dir=tmp_path,
        http_get=http_get,
    )

    assert pub_res.success is True
    assert pub_res.format == "html"
    assert pre_res.success is True
    assert pre_res.format == "html"

    # Key behavior: preprint should NOT try PDF/XML first in this case
    assert calls == [
        "https://example.org/published.html",
        "https://example.org/preprint.html",
    ]
