from __future__ import annotations

"""Matched-pair corpus assembly and full-text acquisition.

This module connects preprint metadata extraction to full-text acquisition for
Study 1's primary comparator:

- select the first publicly posted preprint version for each DOI,
- require a corresponding published DOI for inclusion in acquisition,
- build deterministic full-text acquisition requests for both versions, and
- download both sides through the existing acquisition primitives.

The implementation is intentionally I/O-light and testable. URL construction and
pair selection are pure functions; network access is still injected through the
same `http_get` callable used by `peer_elt.acquire.full_text`.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

import pandas as pd

from peer_elt.config import RetryConfig, SourceConfig
from peer_elt.acquire.full_text import (
    AcquisitionRequest,
    AcquisitionResult,
    HttpGet,
    acquire_full_text_pair,
)
from peer_elt.interfaces import Extractor


@dataclass(frozen=True)
class MatchedManuscriptPair:
    """Metadata needed to acquire a matched preprint/published pair.

    Attributes
    ----------
    manuscript_id : str
        Stable pair identifier, typically ``"<server>:<preprint_doi>"``.
    server : str
        Preprint server slug, currently ``"biorxiv"`` or ``"medrxiv"``.
    preprint_doi : str
        DOI of the preprint manuscript.
    preprint_version : str
        Version identifier selected as the preregistered baseline comparator.
    preprint_date : str | None
        Posting date for the selected preprint version when available.
    published_doi : str
        DOI of the matched peer-reviewed published article.
    """

    manuscript_id: str
    server: str
    preprint_doi: str
    preprint_version: str
    preprint_date: str | None
    published_doi: str


@dataclass(frozen=True)
class PairAcquisitionResult:
    """Full-text acquisition result for a matched manuscript pair.

    Attributes
    ----------
    pair : MatchedManuscriptPair
        Pair metadata used to construct the acquisition requests.
    preprint : peer_elt.acquire.full_text.AcquisitionResult
        Download result for the selected initial preprint version.
    published : peer_elt.acquire.full_text.AcquisitionResult
        Download result for the matched published article.
    """

    pair: MatchedManuscriptPair
    preprint: AcquisitionResult
    published: AcquisitionResult


def query_preprint_servers_for_pairs(
        sources: Iterable[SourceConfig],
        extractor: Extractor,
        retry_config: RetryConfig,
) -> list[MatchedManuscriptPair]:
    """Query configured preprint sources and build matched manuscript pairs.

    Parameters
    ----------
    sources : Iterable[peer_elt.config.SourceConfig]
        Source configurations defining server slugs and date windows.
    extractor : peer_elt.interfaces.Extractor
        Metadata extractor used to query each configured source.
    retry_config : peer_elt.config.RetryConfig
        Retry/backoff settings forwarded to the extractor.

    Returns
    -------
    list[MatchedManuscriptPair]
        Matched manuscript pairs that have an initial preprint version and a
        corresponding published DOI.
    """
    frames: list[pd.DataFrame] = []
    for source in sources:
        frame = extractor.fetch(source, retry_config)
        if frame.empty:
            continue
        frames.append(frame)

    if not frames:
        return []
    raw_df = pd.concat(frames, ignore_index=True)
    return build_matched_manuscript_pairs(raw_df)


def build_matched_manuscript_pairs(raw_df: pd.DataFrame) -> list[MatchedManuscriptPair]:
    """Build matched pairs from raw preprint metadata.

    The preprint side always uses the earliest version for each `(server, doi)`.
    The published side uses the first non-empty `published_doi`/`published`
    value observed for that preprint across versions. Records with no published
    DOI are omitted because there is no matched published article to acquire.

    Parameters
    ----------
    raw_df : pandas.DataFrame
        Raw preprint metadata. Required columns are ``doi``, ``server``, and
        ``version``. Optional columns include ``date``, ``published_doi``, and
        ``published``.

    Returns
    -------
    list[MatchedManuscriptPair]
        One matched pair per `(server, doi)` group with a published DOI.

    Raises
    ------
    KeyError
        If required metadata columns are missing.
    """
    if raw_df.empty:
        return []

    required = {"doi", "server", "version"}
    missing = required - set(raw_df.columns)
    if missing:
        raise KeyError(f"Raw metadata missing required columns: {sorted(missing)}")

    frame = raw_df.copy()
    frame["doi"] = frame["doi"].map(_clean_optional_text)
    frame["server"] = frame["server"].map(_clean_optional_text)
    frame["version_sort"] = pd.to_numeric(frame["version"], errors="coerce")
    frame["version_sort"] = frame["version_sort"].fillna(float("inf"))

    if "published_doi" in frame.columns:
        published = frame["published_doi"]
    else:
        published = pd.Series([None] * len(frame), index=frame.index)
    if "published" in frame.columns:
        published = published.where(published.notna(), frame["published"])
    frame["published_doi"] = published
    frame["published_doi"] = frame["published_doi"].map(_clean_optional_text)

    pairs: list[MatchedManuscriptPair] = []
    for (server, doi), group in frame.groupby(["server", "doi"], sort=True):
        if not server or not doi:
            continue

        published_doi = _first_non_empty(group["published_doi"])
        if not published_doi:
            continue

        sort_columns = ["version_sort"]
        if "date" in group.columns:
            sort_columns.append("date")
        initial = group.sort_values(sort_columns, na_position="last").iloc[0]
        preprint_version = _format_version(initial["version"])
        preprint_date = _clean_optional_text(initial.get("date"))
        manuscript_id = f"{server}:{doi}"

        pairs.append(
            MatchedManuscriptPair(
                manuscript_id=manuscript_id,
                server=server,
                preprint_doi=doi,
                preprint_version=preprint_version,
                preprint_date=preprint_date,
                published_doi=published_doi,
            )
        )

    return pairs


def build_acquisition_requests(
        pair: MatchedManuscriptPair,
) -> tuple[AcquisitionRequest, AcquisitionRequest]:
    """Create full-text acquisition requests for a matched pair.

    Parameters
    ----------
    pair : MatchedManuscriptPair
        Pair metadata containing the selected initial preprint version and
        matched published DOI.

    Returns
    -------
    tuple[AcquisitionRequest, AcquisitionRequest]
        Preprint and published-article acquisition requests, respectively.
    """
    preprint_url_base = _preprint_content_url(pair.server, pair.preprint_doi, pair.preprint_version)
    preprint = AcquisitionRequest(
        doc_id=_safe_doc_id(f"{pair.server}_{pair.preprint_doi}_v{pair.preprint_version}_preprint"),
        pdf_url=f"{preprint_url_base}.full.pdf",
        xml_url=f"{preprint_url_base}.source.xml",
        html_url=preprint_url_base,
    )
    published = AcquisitionRequest(
        doc_id=_safe_doc_id(f"doi_{pair.published_doi}_published"),
        pdf_url=None,
        xml_url=None,
        html_url=f"https://doi.org/{pair.published_doi}",
    )
    return preprint, published


def acquire_matched_pair_full_text(
        pair: MatchedManuscriptPair,
        base_dir: Path,
        http_get: HttpGet,
        timeout_seconds: float = 30.0,
) -> PairAcquisitionResult:
    """Download the initial preprint version and published version.

    Parameters
    ----------
    pair : MatchedManuscriptPair
        Matched pair to acquire.
    base_dir : pathlib.Path
        Directory under which downloaded artifacts are saved.
    http_get : peer_elt.acquire.full_text.HttpGet
        Injected HTTP getter used for deterministic testing and production
        retry behavior.
    timeout_seconds : float, default=30.0
        Per-request timeout passed to the downloader.

    Returns
    -------
    PairAcquisitionResult
        Pair metadata plus acquisition results for both manuscript versions.
    """
    preprint_request, published_request = build_acquisition_requests(pair)
    preprint_result, published_result = acquire_full_text_pair(
        preprint=preprint_request,
        published=published_request,
        base_dir=base_dir,
        http_get=http_get,
        timeout_seconds=timeout_seconds,
    )
    return PairAcquisitionResult(
        pair=pair,
        preprint=preprint_result,
        published=published_result,
    )


def acquire_corpus_full_text(
        pairs: Iterable[MatchedManuscriptPair],
        base_dir: Path,
        http_get: HttpGet,
        timeout_seconds: float = 30.0,
) -> list[PairAcquisitionResult]:
    """Download full text for an iterable of matched manuscript pairs.

    Parameters
    ----------
    pairs : Iterable[MatchedManuscriptPair]
        Matched manuscript pairs to acquire.
    base_dir : pathlib.Path
        Directory under which downloaded artifacts are saved.
    http_get : peer_elt.acquire.full_text.HttpGet
        Injected HTTP getter.
    timeout_seconds : float, default=30.0
        Per-request timeout passed to each acquisition call.

    Returns
    -------
    list[PairAcquisitionResult]
        Acquisition results in the same order as the input pairs.
    """
    return [
        acquire_matched_pair_full_text(
            pair=pair,
            base_dir=base_dir,
            http_get=http_get,
            timeout_seconds=timeout_seconds,
        )
        for pair in pairs
    ]


def _preprint_content_url(server: str, doi: str, version: str) -> str:
    """Return the bioRxiv/medRxiv content URL for a DOI version.

    Parameters
    ----------
    server : str
        Preprint server slug.
    doi : str
        Preprint DOI.
    version : str
        Preprint version identifier.

    Returns
    -------
    str
        Version-specific preprint content URL.

    Raises
    ------
    ValueError
        If URL construction is requested for an unsupported server.
    """
    if server not in {"biorxiv", "medrxiv"}:
        raise ValueError(f"Unsupported preprint server for URL construction: {server}")
    return f"https://www.{server}.org/content/{doi}v{version}"


def _clean_optional_text(value) -> str | None:
    """Normalize optional string-like metadata values.

    Parameters
    ----------
    value
        Raw metadata value.

    Returns
    -------
    str | None
        Trimmed string value, or None for null/empty sentinel values.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "na"}:
        return None
    return text


def _first_non_empty(values) -> str | None:
    """Return the first normalized non-empty value from a sequence.

    Parameters
    ----------
    values
        Iterable of metadata values.

    Returns
    -------
    str | None
        First non-empty normalized string, or None when no value is available.
    """
    for value in values:
        text = _clean_optional_text(value)
        if text:
            return text
    return None


def _format_version(value) -> str:
    """Format API version values as stable strings for URLs and IDs.

    Parameters
    ----------
    value
        Raw version value from preprint metadata.

    Returns
    -------
    str
        Version string with integer-like values normalized without decimals.

    Raises
    ------
    ValueError
        If the version value is missing.
    """
    text = _clean_optional_text(value)
    if text is None:
        raise ValueError("Preprint version is required")
    try:
        numeric = float(text)
    except ValueError:
        return text
    if numeric.is_integer():
        return str(int(numeric))
    return text


def _safe_doc_id(value: str) -> str:
    """Return a filesystem-friendly document identifier.

    Parameters
    ----------
    value : str
        Raw identifier string.

    Returns
    -------
    str
        Identifier containing only alphanumeric characters, dots, underscores,
        and hyphens.
    """
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
