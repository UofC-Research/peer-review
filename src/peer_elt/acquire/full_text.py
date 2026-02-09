from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Mapping, Optional, Sequence

AcquiredFormat = Literal["pdf", "xml", "html"]


@dataclass(frozen=True)
class AcquisitionRequest:
    doc_id: str
    pdf_url: Optional[str]
    xml_url: Optional[str]
    html_url: Optional[str]


@dataclass(frozen=True)
class AcquisitionResult:
    doc_id: str
    success: bool
    format: Optional[AcquiredFormat]
    url: Optional[str]
    path: Optional[Path]
    needs_human_confirmation: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class _ResponseLike:
    status_code: int
    content: bytes
    headers: Mapping[str, str]


HttpGet = Callable[[str, float], _ResponseLike]


def _is_success(resp: _ResponseLike) -> bool:
    if resp.status_code != 200:
        return False
    if not resp.content:
        return False
    return True


def _target_path(base_dir: Path, doc_id: str, fmt: AcquiredFormat) -> Path:
    doc_dir = base_dir / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    suffix = {"pdf": ".pdf", "xml": ".xml", "html": ".html"}[fmt]
    return doc_dir / f"full_text{suffix}"


def _url_for_format(request: AcquisitionRequest, fmt: AcquiredFormat) -> Optional[str]:
    if fmt == "pdf":
        return request.pdf_url
    if fmt == "xml":
        return request.xml_url
    return request.html_url


def _available_formats(request: AcquisitionRequest) -> list[AcquiredFormat]:
    formats: list[AcquiredFormat] = []
    if request.pdf_url:
        formats.append("pdf")
    if request.xml_url:
        formats.append("xml")
    if request.html_url:
        formats.append("html")
    return formats


def acquire_full_text(
        request: AcquisitionRequest,
        base_dir: Path,
        http_get: HttpGet,
        timeout_seconds: float = 30.0,
        attempt_order: Sequence[AcquiredFormat] = ("pdf", "xml", "html"),
) -> AcquisitionResult:
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

    Rule:
    - If the *published* version has exactly one available format (e.g., HTML only),
      then force the *preprint* acquisition to use that same format first/only.
    - Otherwise both use the default order (pdf -> xml -> html).

    Returns (preprint_result, published_result).
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
