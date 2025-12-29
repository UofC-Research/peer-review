from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import requests
from peer_elt.config import SourceConfig
from peer_elt.interfaces import Extractor

API_ROOT = "https://api.biorxiv.org/details"


def _fetch_page(server: str, date_from: str, date_to: str, cursor: int) -> Dict[str, Any]:
    url = f"{API_ROOT}/{server}/{date_from}/{date_to}/{cursor}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def fetch_preprints(server: str, date_from: str, date_to: str) -> pd.DataFrame:
    cursor = 0
    records: List[Dict[str, Any]] = []

    while True:
        payload = _fetch_page(server, date_from, date_to, cursor)
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


class BiorxivApiExtractor(Extractor):
    def fetch(self, source: SourceConfig) -> pd.DataFrame:
        return fetch_preprints(
            server=source.server,
            date_from=source.date_from,
            date_to=source.date_to,
        )
