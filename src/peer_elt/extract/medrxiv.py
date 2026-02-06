from __future__ import annotations

"""Convenience wrapper for medRxiv extraction.

This module exposes a small helper function that delegates to
:func:`peer_elt.extract.biorxiv.fetch_preprints` with ``server="medrxiv"``.
"""

import pandas as pd

from peer_elt.extract.biorxiv import fetch_preprints


def fetch_medrxiv(date_from: str, date_to: str, retry_config) -> pd.DataFrame:
    """Fetch medRxiv metadata for a date window.

    Parameters
    ----------
    date_from : str
        Inclusive start date in ``YYYY-MM-DD`` format.
    date_to : str
        Inclusive end date in ``YYYY-MM-DD`` format.
    retry_config
        Retry/backoff configuration forwarded to
        :func:`peer_elt.extract.biorxiv.fetch_preprints` (typically a
        ``RetryConfig``).

    Returns
    -------
    pandas.DataFrame
        DataFrame of raw metadata returned by the public API. If the API returns
        no records for the window, an empty DataFrame is returned.
    """
    return fetch_preprints(
        server="medrxiv",
        date_from=date_from,
        date_to=date_to,
        retry_config=retry_config,
    )
