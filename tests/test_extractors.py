import pandas as pd

from peer_elt.config import RetryConfig
from peer_elt.extract import biorxiv, medrxiv


def test_fetch_preprints_paginates_and_sets_fields(monkeypatch) -> None:
    payloads = {
        0: {
            "collection": [
                {"doi": "10.1/a", "published": "10.2/a"},
                {"doi": "10.1/b", "published": None},
            ],
            "total": 3,
        },
        2: {
            "collection": [
                {"doi": "10.1/c", "published": "10.2/c"},
            ],
            "total": 3,
        },
    }

    class DummyResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    def fake_get(url, timeout):
        cursor = int(url.split("/")[-1])
        return DummyResponse(payloads.get(cursor, {"collection": [], "total": 0}))

    monkeypatch.setattr(biorxiv.requests, "get", fake_get)

    df = biorxiv.fetch_preprints(
        server="biorxiv",
        date_from="2023-01-01",
        date_to="2023-01-02",
        retry_config=RetryConfig(max_attempts=1, wait_min_seconds=0, wait_max_seconds=0),
    )

    assert df.shape[0] == 3
    assert set(df["server"]) == {"biorxiv"}
    assert "published_doi" in df.columns


def test_fetch_medrxiv_passes_server(monkeypatch) -> None:
    called = {}

    def fake_fetch_preprints(server, date_from, date_to, retry_config):
        called["args"] = (server, date_from, date_to, retry_config)
        return pd.DataFrame()

    monkeypatch.setattr(medrxiv, "fetch_preprints", fake_fetch_preprints)

    retry = RetryConfig()
    medrxiv.fetch_medrxiv("2023-01-01", "2023-01-02", retry)

    assert called["args"][0] == "medrxiv"
