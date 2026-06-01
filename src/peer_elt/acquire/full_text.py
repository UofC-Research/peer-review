from __future__ import annotations

"""Full-text acquisition (download) for manuscript versions.

This module provides small, testable primitives for retrieving full text for:

- a single manuscript version (preprint OR published), and
- a matched preprint/published pair.

The central idea is that acquisition is **I/O only**: this module downloads bytes,
persists them, and records a structured outcome. It does *not* parse PDFs/XML/HTML;
parsing and sectionization are handled elsewhere (e.g., under ``peer_elt.parse``).

Key behaviors
-------------
1) Format fallback for a single document (default: PDF → XML → HTML):
   - Try each representation in ``attempt_order``.
   - On first successful retrieval, write bytes to disk and return success.
   - If all attempts fail, return a result flagged for human confirmation.

2) Pair-aware harmonization (matched preprint/published pair):
   - If the published version has exactly one available format (e.g., HTML only),
     force the preprint acquisition to use that same format. This reduces format
     mismatch when one side is constrained by access.

Testability
-----------
Network access is injected via ``http_get`` (a callable). This keeps unit tests fast
and deterministic and lets production code use a robust HTTP implementation (e.g.,
requests + tenacity retries) without coupling tests to the network.

Persistence layout
------------------
On success, retrieved bytes are written to::

    <base_dir>/<doc_id>/full_text.<ext>

Where <ext> is ``pdf``, ``xml``, or ``html``.

Human confirmation semantics
----------------------------
This module flags human confirmation whenever it cannot automatically retrieve a
full-text artifact. The caller should log and surface these cases for inspection.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Mapping, Optional, Sequence

AcquiredFormat = Literal["pdf", "xml", "html"]


@dataclass(frozen=True)
class AcquisitionRequest:
    """Input describing where to retrieve a manuscript's full text.

    Attributes
    ----------
    doc_id:
        Stable identifier used for output folder naming.
    pdf_url, xml_url, html_url:
        Candidate URLs for each representation. Any may be ``None``.
    """

    doc_id: str
    pdf_url: Optional[str]
    xml_url: Optional[str]
    html_url: Optional[str]


@dataclass(frozen=True)
class AcquisitionResult:
    """Outcome of a full-text acquisition attempt."""

    doc_id: str
    success: bool
    format: Optional[AcquiredFormat]
    url: Optional[str]
    path: Optional[Path]
    needs_human_confirmation: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class _ResponseLike:
    """Minimal response contract for injected HTTP getters."""

    status_code: int
    content: bytes
    headers: Mapping[str, str]


HttpGet = Callable[[str, float], _ResponseLike]


def _is_success(resp: _ResponseLike) -> bool:
    """Return True if an HTTP response should be treated as a successful download."""
    if resp.status_code != 200:
        return False
    if not resp.content:
        return False
    return True


def _target_path(base_dir: Path, doc_id: str, fmt: AcquiredFormat) -> Path:
    """Compute the destination path for a downloaded artifact and ensure its folder exists."""
    doc_dir = base_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    suffix = {"pdf": ".pdf", "xml": ".xml", "html": ".html"}[fmt]
    return doc_dir / f"full_text{suffix}"


def _url_for_format(request: AcquisitionRequest, fmt: AcquiredFormat) -> Optional[str]:
    """Return the URL corresponding to the desired format."""
    if fmt == "pdf":
        return request.pdf_url
    if fmt == "xml":
        return request.xml_url
    return request.html_url


def _available_formats(request: AcquisitionRequest) -> list[AcquiredFormat]:
    """List formats that have a non-null URL for this request."""
    return [
        fmt
        for fmt in ("pdf", "xml", "html")
        if _url_for_format(request, fmt)
    ]


def acquire_full_text(
        request: AcquisitionRequest,
        base_dir: Path,
        http_get: HttpGet,
        timeout_seconds: float = 30.0,
        attempt_order: Sequence[AcquiredFormat] = ("pdf", "xml", "html"),
) -> AcquisitionResult:
    """Acquire a single manuscript's full text with format fallback.

    Parameters
    ----------
    request:
        AcquisitionRequest containing URLs for PDF/XML/HTML.
    base_dir:
        Root directory under which to store retrieved artifacts.
    http_get:
        Injected HTTP getter: ``(url, timeout_seconds) -> response-like``.
    timeout_seconds:
        Per-request timeout passed through to ``http_get``.
    attempt_order:
        Ordered formats to attempt. Defaults to ``("pdf", "xml", "html")``.

    Returns
    -------
    AcquisitionResult
        - On success: ``success=True``, ``format`` set, ``path`` points to saved file.
        - On failure: ``success=False``, ``needs_human_confirmation=True``, and an
          explanatory ``error_message``.

    Human confirmation semantics
    ----------------------------
    Any failure is flagged for human confirmation because it may reflect:
    - true inaccessibility,
    - transient network problems,
    - upstream metadata problems (bad URLs),
    - or platform-specific access constraints.
    """
    attempts: Sequence[tuple[AcquiredFormat, Optional[str]]] = tuple(
        (fmt, _url_for_format(request, fmt)) for fmt in attempt_order
    )

    provided = [fmt for fmt, url in attempts if url]
    if not provided:
        return AcquisitionResult(
            doc_id=request.doc_id,
            success=False,
            format=None,
            url=None,
            path=None,
            needs_human_confirmation=True,
            error_message="No full-text URLs provided (pdf/xml/html). Flagged for human confirmation.",
        )

    last_error: Optional[str] = None

    for fmt, url in attempts:
        if not url:
            last_error = f"Missing URL for {fmt}"
            continue

        try:
            resp = http_get(url, timeout_seconds)
        except Exception as e:  # keep deterministic behavior; callers can log details upstream
            last_error = f"{fmt.upper()} request failed: {e.__class__.__name__}"
            continue

        if not _is_success(resp):
            last_error = f"{fmt.upper()} retrieval failed with status {resp.status_code}"
            continue

        path = _target_path(base_dir=base_dir, doc_id=request.doc_id, fmt=fmt)
        path.write_bytes(resp.content)

        return AcquisitionResult(
            doc_id=request.doc_id,
            success=True,
            format=fmt,
            url=url,
            path=path,
            needs_human_confirmation=False,
            error_message=None,
        )

    return AcquisitionResult(
        doc_id=request.doc_id,
        success=False,
        format=None,
        url=None,
        path=None,
        needs_human_confirmation=True,
        error_message=f"All retrieval attempts failed. Last error: {last_error}",
    )


def acquire_full_text_pair(
        preprint: AcquisitionRequest,
        published: AcquisitionRequest,
        base_dir: Path,
        http_get: HttpGet,
        timeout_seconds: float = 30.0,
) -> tuple[AcquisitionResult, AcquisitionResult]:
    """Acquire full text for a matched preprint/published pair.

    Rule
    ----
    If the published version has exactly one available format, acquire *both*
    versions using that format (and only that format). This reduces format
    mismatch when one side is constrained.

    Otherwise, acquire each independently using the default attempt order.

    Returns
    -------
    (preprint_result, published_result)
    """
    published_formats = _available_formats(published)

    pub_attempt_order: Sequence[AcquiredFormat] = ("pdf", "xml", "html")
    pre_attempt_order: Sequence[AcquiredFormat] = ("pdf", "xml", "html")

    if len(published_formats) == 1:
        only = published_formats[0]
        pub_attempt_order = (only,)
        pre_attempt_order = (only,)

    pub_res = acquire_full_text(
        published,
        base_dir=base_dir,
        http_get=http_get,
        timeout_seconds=timeout_seconds,
        attempt_order=pub_attempt_order,
    )
    pre_res = acquire_full_text(
        preprint,
        base_dir=base_dir,
        http_get=http_get,
        timeout_seconds=timeout_seconds,
        attempt_order=pre_attempt_order,
    )
    return pre_res, pub_res
