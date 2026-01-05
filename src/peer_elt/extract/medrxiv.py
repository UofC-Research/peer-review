from __future__ import annotations

"""Convenience wrapper for medRxiv extraction."""

import pandas as pd

from peer_elt.extract.biorxiv import fetch_preprints


def fetch_medrxiv(date_from: str, date_to: str, retry_config) -> pd.DataFrame:
    """Fetch medRxiv metadata for the given date range."""
    return fetch_preprints(
        server="medrxiv",
        date_from=date_from,
        date_to=date_to,
        retry_config=retry_config,
    )
