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


def acquire_full_text(
        request: AcquisitionRequest,
        base_dir: Path,
        http_get: HttpGet,
        timeout_seconds: float = 30.0,
) -> AcquisitionResult:
    attempts: Sequence[tuple[AcquiredFormat, Optional[str]]] = (
        ("pdf", request.pdf_url),
        ("xml", request.xml_url),
        ("html", request.html_url),
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
