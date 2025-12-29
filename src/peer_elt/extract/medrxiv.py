from __future__ import annotations

import pandas as pd

from peer_elt.extract.biorxiv import fetch_preprints


def fetch_medrxiv(date_from: str, date_to: str) -> pd.DataFrame:
    return fetch_preprints(server="medrxiv", date_from=date_from, date_to=date_to)
