"""Tests for extractor helpers and registry-based dispatch.

These tests validate:
- pagination and normalization behavior for the bioRxiv/medRxiv API helper, and
- that the registry-based extractor dispatches to the correct client.
"""

import pandas as pd

from peer_elt.config import RetryConfig, SourceConfig
from peer_elt.extract import biorxiv, medrxiv
from peer_elt.extract.registry import PreprintServerClient, PreprintServerRegistry, RegistryExtractor


def test_fetch_preprints_paginates_and_sets_fields(monkeypatch) -> None:
    """Paginate through API results and normalize expected output fields.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to stub `requests.get`.

    Asserts:
        The returned DataFrame contains all pages, sets the `server` column,
        and includes a `published_doi` column.
    """
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
        """Response stub mimicking the subset of `requests.Response` used."""

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
    """Delegate to `fetch_preprints` with server set to `medrxiv`.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to stub `fetch_preprints`.

    Asserts:
        The delegated call uses `server="medrxiv"`.
    """
    called = {}

    def fake_fetch_preprints(server, date_from, date_to, retry_config):
        called["args"] = (server, date_from, date_to, retry_config)
        return pd.DataFrame()

    monkeypatch.setattr(medrxiv, "fetch_preprints", fake_fetch_preprints)

    retry = RetryConfig()
    medrxiv.fetch_medrxiv("2023-01-01", "2023-01-02", retry)

    assert called["args"][0] == "medrxiv"


def test_registry_extractor_fetches_from_registered_client() -> None:
    """Fetch using a registered client selected by server slug.

    Asserts:
        The registry extractor dispatches to the registered client and preserves
        the expected `server` value in the output.
    """
    class DummyClient(PreprintServerClient):
        """Client stub registered under a fake server slug."""
        server = "dummy"

        def fetch(self, date_from, date_to, retry_config):
            return pd.DataFrame([{"doi": "10.1/x", "server": self.server}])

    registry = PreprintServerRegistry()
    registry.register(DummyClient())
    extractor = RegistryExtractor(registry)

    source = SourceConfig(
        name="dummy",
        server="dummy",
        date_from="2023-01-01",
        date_to="2023-01-02",
    )
    df = extractor.fetch(source=source, retry_config=RetryConfig())

    assert df.iloc[0]["server"] == "dummy"
