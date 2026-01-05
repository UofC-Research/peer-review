import json
import sys

import pandas as pd
from peer_elt import cli
from peer_elt.config import (
    OutputConfig,
    PipelineConfig,
    RetryConfig,
    SourceConfig,
    StorageConfig,
    TransformConfig,
    load_config,
)
from peer_elt.pipeline import extract_sources, run_pipeline, write_outputs


def test_load_config_expands_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_DB_URL", "postgresql://user:pass@localhost/db")
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: \"2023-01-01\"",
                "    date_to: \"2023-01-02\"",
                "storage:",
                "  backend: postgres",
                "  postgres_url: \"${TEST_DB_URL}\"",
                "output:",
                "  base_dir: \"data/out\"",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.storage.postgres_url == "postgresql://user:pass@localhost/db"
    assert config.retry.max_attempts == 5


def test_extract_sources_combines_and_tags() -> None:
    sources = [
        SourceConfig(
            name="bio",
            server="biorxiv",
            date_from="2023-01-01",
            date_to="2023-01-02",
        ),
        SourceConfig(
            name="med",
            server="medrxiv",
            date_from="2023-01-01",
            date_to="2023-01-02",
        ),
    ]

    class DummyExtractor:
        def __init__(self, server: str) -> None:
            self._server = server

        def fetch(self, source, retry_config):
            return pd.DataFrame([{"doi": f"10.1/{self._server}", "server": self._server}])

    class DummyFactory:
        def create(self, source):
            return DummyExtractor(source.server)

    output = extract_sources(sources, DummyFactory(), RetryConfig())

    assert output.shape[0] == 2
    assert set(output["source_name"]) == {"bio", "med"}


def test_write_outputs_writes_files_and_calls_storage(tmp_path) -> None:
    config = PipelineConfig(
        sources=[],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir=str(tmp_path), write_csv=True),
        transform=TransformConfig(),
        retry=RetryConfig(),
    )

    class DummyStorage:
        def __init__(self) -> None:
            self.calls = []

        def write_table(self, table_name: str, df: pd.DataFrame) -> None:
            self.calls.append((table_name, df.copy()))

    df = pd.DataFrame([{"doi": "10.1/abc", "metric": 1.0}])
    storage = DummyStorage()

    write_outputs(storage, config, df, "diff_features")

    assert (tmp_path / "diff_features.parquet").exists()
    assert (tmp_path / "diff_features.csv").exists()
    assert storage.calls[0][0] == "diff_features"


def test_run_pipeline_returns_zero_when_empty(monkeypatch) -> None:
    config = PipelineConfig(
        sources=[
            SourceConfig(
                name="bio",
                server="biorxiv",
                date_from="2023-01-01",
                date_to="2023-01-02",
            )
        ],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir="data/out"),
        transform=TransformConfig(),
        retry=RetryConfig(),
    )

    class DummyExtractor:
        def fetch(self, source, retry_config):
            return pd.DataFrame()

    class DummyExtractorFactory:
        def create(self, source):
            return DummyExtractor()

    class DummyStorageFactory:
        def create(self, storage):
            return object()

    class DummyTransformerFactory:
        def create(self, config):
            return object()

    monkeypatch.setattr(
        "peer_elt.pipeline.ExtractorFactory", DummyExtractorFactory
    )
    monkeypatch.setattr("peer_elt.pipeline.StorageFactory", DummyStorageFactory)
    monkeypatch.setattr(
        "peer_elt.pipeline.TransformerFactory", DummyTransformerFactory
    )

    result = run_pipeline(config)

    assert result == {"raw_rows": 0, "diff_rows": 0}


def test_cli_extract_prints_counts(monkeypatch, capsys) -> None:
    config = PipelineConfig(
        sources=[
            SourceConfig(
                name="bio",
                server="biorxiv",
                date_from="2023-01-01",
                date_to="2023-01-02",
            )
        ],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir="data/out"),
        transform=TransformConfig(),
        retry=RetryConfig(),
    )

    class DummyExtractorFactory:
        def create(self, source):
            return object()

    class DummyStorage:
        def load_raw(self, df: pd.DataFrame) -> None:
            return None

    class DummyStorageFactory:
        def create(self, storage):
            return DummyStorage()

    class DummyTransformerFactory:
        def create(self, config):
            return object()

    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "ExtractorFactory", DummyExtractorFactory)
    monkeypatch.setattr(cli, "StorageFactory", DummyStorageFactory)
    monkeypatch.setattr(cli, "TransformerFactory", DummyTransformerFactory)
    monkeypatch.setattr(
        cli,
        "extract_sources",
        lambda sources, extractor_factory, retry_config: pd.DataFrame([{"x": 1}]),
    )
    monkeypatch.setattr(cli, "load_raw", lambda storage, raw_df: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["peer-elt", "--config", "config.yml", "extract"],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["raw_rows"] == 1
