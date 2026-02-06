from __future__ import annotations

"""Extractor for bioRxiv/medRxiv metadata via the public API."""

from typing import Any, Dict, List

import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from peer_elt.config import RetryConfig, SourceConfig
from peer_elt.extract.registry import PreprintServerClient
from peer_elt.interfaces import Extractor

API_ROOT = "https://api.biorxiv.org/details"


def _fetch_page(
        server: str,
        date_from: str,
        date_to: str,
        cursor: int,
        retry_config: RetryConfig,
) -> Dict[str, Any]:
    """Call the bioRxiv/medRxiv details API for a page of results.

    Args:
        server: "biorxiv" or "medrxiv".
        date_from: Inclusive start date in YYYY-MM-DD.
        date_to: Inclusive end date in YYYY-MM-DD.
        cursor: Offset cursor for pagination.
    """
    url = f"{API_ROOT}/{server}/{date_from}/{date_to}/{cursor}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def fetch_preprints(
        server: str,
        date_from: str,
        date_to: str,
        retry_config: RetryConfig,
) -> pd.DataFrame:
    """Fetch all preprints between date_from and date_to for a server.

    Returns:
        DataFrame with raw metadata fields returned by the API.
    """
    cursor = 0
    records: List[Dict[str, Any]] = []
    fetch_with_retry = retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        wait=wait_exponential(
            multiplier=retry_config.wait_multiplier,
            min=retry_config.wait_min_seconds,
            max=retry_config.wait_max_seconds,
        ),
        stop=stop_after_attempt(retry_config.max_attempts),
        reraise=True,
    )(_fetch_page)

    while True:
        payload = fetch_with_retry(server, date_from, date_to, cursor, retry_config)
        items = payload.get("collection", [])
        if not items:
            break
        records.extend(items)
        cursor += len(items)
        if cursor >= int(payload.get("total", 0)):
            break

    if not records:
        return pd.DataFrame()

    frame = pd.DataFrame.from_records(records)
    frame["server"] = server
    frame["published_doi"] = frame.get("published")
    return frame


class BiorxivApiClient(PreprintServerClient):
    """Client that uses the bioRxiv/medRxiv public API."""

    def __init__(self, server: str) -> None:
        self.server = server

    def fetch(self, date_from: str, date_to: str, retry_config: RetryConfig) -> pd.DataFrame:
        return fetch_preprints(
            server=self.server,
            date_from=date_from,
            date_to=date_to,
            retry_config=retry_config,
        )


class BiorxivApiExtractor(Extractor):
    """Extractor that uses the bioRxiv/medRxiv public API."""

    def __init__(self, client: BiorxivApiClient | None = None) -> None:
        self._client = client

    def fetch(self, source: SourceConfig, retry_config: RetryConfig) -> pd.DataFrame:
        """Fetch records for the configured source window.

        Args:
            source: Source configuration with server and date range.
        """
        client = self._client or BiorxivApiClient(server=source.server)
        return client.fetch(source.date_from, source.date_to, retry_config)
