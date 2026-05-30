from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import requests

from peer_elt.acquire.corpus import (
    MatchedManuscriptPair,
    acquire_matched_pair_full_text,
    build_acquisition_requests,
)
from peer_elt.acquire.full_text import acquire_full_text
from peer_elt.acquire.http import RequestsHttpGet
from peer_elt.config import RetryConfig
from peer_elt.extract.biorxiv import fetch_preprints

pytestmark = pytest.mark.live


def _retry_config(payload: dict[str, Any]) -> RetryConfig:
    retry = payload.get("retry") or {}
    if not isinstance(retry, dict):
        raise TypeError("live test config `retry` must be a mapping")
    return RetryConfig(**retry)


def _http_get(payload: dict[str, Any]) -> RequestsHttpGet:
    return RequestsHttpGet(
        session=requests.Session(),
        retry=_retry_config(payload),
    )


def test_live_preprint_sources_return_expected_metadata(live_config: dict[str, Any]) -> None:
    """Validate configured live preprint API windows still return expected metadata."""
    sources = live_config.get("preprint_sources") or []
    if not sources:
        pytest.skip("no live preprint_sources configured")

    for source in sources:
        frame = fetch_preprints(
            server=source["server"],
            date_from=source["date_from"],
            date_to=source["date_to"],
            retry_config=_retry_config(live_config),
        )

        assert len(frame) >= int(source.get("min_records", 1)), source["name"]
        assert set(frame["server"]) == {source["server"]}

        required_columns = set(source.get("required_columns") or [])
        missing_columns = required_columns - set(frame.columns)
        assert not missing_columns, f"{source['name']} missing columns: {missing_columns}"


def test_live_published_full_text_candidates_are_retrievable(
        live_config: dict[str, Any],
        tmp_path: Path,
) -> None:
    """Validate configured publisher DOI candidates can retrieve some full text."""
    cases = live_config.get("published_full_text") or []
    if not cases:
        pytest.skip("no live published_full_text cases configured")

    http_get = _http_get(live_config)
    timeout_seconds = float(live_config.get("timeout_seconds", 20))

    for case in cases:
        pair = MatchedManuscriptPair(
            manuscript_id=f"live:{case['published_doi']}",
            server="biorxiv",
            preprint_doi="10.1101/live-placeholder",
            preprint_version="1",
            preprint_date=None,
            published_doi=case["published_doi"],
        )
        _, published = build_acquisition_requests(pair)

        result = acquire_full_text(
            request=published,
            base_dir=tmp_path,
            http_get=http_get,
            timeout_seconds=timeout_seconds,
        )

        assert result.success is True, f"{case['name']}: {result.error_message}"
        assert result.format in set(case.get("expected_formats") or ["pdf", "xml", "html"])
        assert result.path is not None
        assert result.path.exists()
        assert result.path.stat().st_size > 0


def test_live_matched_pairs_can_be_acquired(
        live_config: dict[str, Any],
        tmp_path: Path,
) -> None:
    """Optionally validate configured preprint/published pairs through acquisition."""
    cases = live_config.get("matched_pairs") or []
    if not cases:
        pytest.skip("no live matched_pairs configured")

    http_get = _http_get(live_config)
    timeout_seconds = float(live_config.get("timeout_seconds", 20))

    for case in cases:
        pair = MatchedManuscriptPair(
            manuscript_id=case.get("manuscript_id", f"{case['server']}:{case['preprint_doi']}"),
            server=case["server"],
            preprint_doi=case["preprint_doi"],
            preprint_version=str(case["preprint_version"]),
            preprint_date=case.get("preprint_date"),
            published_doi=case["published_doi"],
        )

        result = acquire_matched_pair_full_text(
            pair=pair,
            base_dir=tmp_path,
            http_get=http_get,
            timeout_seconds=timeout_seconds,
        )

        if case.get("require_both_success", True):
            assert result.preprint.success is True, result.preprint.error_message
            assert result.published.success is True, result.published.error_message
        else:
            assert result.preprint.success or result.published.success
