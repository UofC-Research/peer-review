"""Integration-style tests for config loading, pipeline helpers, and CLI wiring.

Scope
-----
These tests sit at the "composition" layer of the project: they validate that
configuration parsing, pipeline helper functions, and CLI entrypoints work
together with minimal stubs.

They intentionally avoid testing business logic of:
- external extractors (network/API correctness),
- real storage backends (DB I/O correctness),
- transformers (feature logic correctness).

Instead, they rely on small dummy implementations plus `monkeypatch` to isolate
behavior and verify contracts (inputs/outputs, raised errors, and side effects).

Coverage map
------------
Config loading (`peer_elt.config.load_config`)
- validates YAML structure and raises clear errors for common mistakes
- expands environment variables in storage settings
- enforces required keys for known backends (duckdb/postgres)
- allows unknown storage backends and preserves extra backend-specific keys
- resolves `output.base_dir` relative to the config file when given a relative path

Pipeline helpers (`peer_elt.pipeline`)
- `extract_sources` merges per-source DataFrames and tags rows with `source_name`
- `write_outputs` writes Parquet/CSV files and delegates persistence to storage
- `run_pipeline` returns a summary and handles empty extraction gracefully

CLI orchestration (`peer_elt.cli`)
- `extract` prints a JSON summary to stdout with expected fields

Testing notes
-------------
- `tmp_path` is used to avoid touching real project directories.
- `monkeypatch` replaces factories and functions to avoid network/DB work.
- Assertions focus on observable effects: raised errors, file creation, and
  printed JSON output.

"""

import json
import sys

import pandas as pd
import pytest

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
from peer_elt.factories import ExtractorFactory
from peer_elt.interfaces import Storage
from peer_elt.pipeline import extract_sources, run_pipeline, write_outputs


def test_load_config_resolves_output_base_dir_relative_to_config_file(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: out",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.output.base_dir == str((tmp_path / "out").resolve())


def test_load_config_raises_when_storage_env_var_unset(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: postgres",
                "  postgres_url: '${UNSET_DB_URL}'",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Unexpanded environment variable in storage\.postgres_url"):
        load_config(config_path)


def test_load_config_allows_storage_env_var_when_set(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SET_DB_URL", "postgresql://<user>:<pass>@<host>/<db>")
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: postgres",
                "  postgres_url: '${SET_DB_URL}'",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.storage.postgres_url == "postgresql://<user>:<pass>@<host>/<db>"


def test_load_config_raises_when_retry_not_mapping(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: 'data/out'",
                "retry: []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match=r"`retry` must be a mapping"):
        load_config(config_path)


def test_load_config_raises_when_transform_not_mapping(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: 'data/out'",
                "transform: []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match=r"`transform` must be a mapping"):
        load_config(config_path)


def test_load_config_raises_clear_error_when_top_level_key_missing(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                # sources missing
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match=r"Top-level config missing required key: sources"):
        load_config(config_path)


def test_load_config_raises_clear_error_when_duckdb_storage_missing_path(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: duckdb",
                "  # duckdb_path intentionally missing",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match=r"Storage backend 'duckdb' requires key: duckdb_path"):
        load_config(config_path)


def test_load_config_raises_clear_error_when_postgres_storage_missing_url(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: postgres",
                "  # postgres_url intentionally missing",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match=r"Storage backend 'postgres' requires key: postgres_url"):
        load_config(config_path)


def test_load_config_allows_unknown_storage_backend_and_preserves_keys(tmp_path) -> None:
    """Unknown backends should be accepted by config loading.

    This keeps config parsing decoupled from which Storage implementations exist.
    """
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: sqlite",
                "  sqlite_path: 'data/app.sqlite'",
                "  pool_size: 5",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.storage.backend == "sqlite"
    assert config.storage.options["sqlite_path"] == "data/app.sqlite"
    assert config.storage.options["pool_size"] == 5


def test_load_config_raises_clear_error_when_source_missing_required_key(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    # date_to intentionally missing",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match=r"Source item 0 missing required key: date_to"):
        load_config(config_path)


def test_load_config_raises_when_source_item_not_mapping(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - just-a-string-not-a-mapping",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="Each item in `sources` must be a mapping"):
        load_config(config_path)


def test_load_config_raises_on_empty_yaml(tmp_path) -> None:
    """Empty YAML should raise a clear error instead of a cryptic TypeError."""
    config_path = tmp_path / "config.yml"
    config_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Empty YAML config"):
        load_config(config_path)


def test_load_config_raises_on_non_mapping_payload(tmp_path) -> None:
    """Top-level YAML must be a mapping/dict."""
    config_path = tmp_path / "config.yml"
    config_path.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(TypeError, match="Top-level YAML config must be a mapping"):
        load_config(config_path)


def test_load_config_expands_env(tmp_path, monkeypatch) -> None:
    """Expand environment variables referenced in the YAML config.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture used to set environment vars.

    Asserts:
        Storage config values expand `${VAR}` placeholders and default retry
        settings are applied when omitted from the YAML.
    """
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


def test_load_config_raises_when_sources_not_list(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources: {}",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="`sources` must be a list"):
        load_config(config_path)


def test_load_config_raises_when_storage_not_mapping(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage: []",
                "output:",
                "  base_dir: 'data/out'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="`storage` must be a mapping"):
        load_config(config_path)


def test_load_config_raises_when_output_not_mapping(tmp_path) -> None:
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: bio",
                "    server: biorxiv",
                "    date_from: '2023-01-01'",
                "    date_to: '2023-01-02'",
                "storage:",
                "  backend: duckdb",
                "  duckdb_path: ':memory:'",
                "output: []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="`output` must be a mapping"):
        load_config(config_path)


def test_extract_sources_combines_and_tags() -> None:
    """Combine extracts from multiple sources and add a `source_name` tag.

    Asserts:
        The combined DataFrame contains one row per source and includes the
        expected `source_name` values.
    """
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
        """Extractor stub returning a single-row DataFrame per server."""

        def __init__(self, server: str) -> None:
            self._server = server

        def fetch(self, source, retry_config):
            return pd.DataFrame([{"doi": f"10.1/{self._server}", "server": self._server}])

    class DummyFactory(ExtractorFactory):
        """Factory stub constructing DummyExtractor from SourceConfig."""

        def create(self, source):
            return DummyExtractor(source.server)

    output = extract_sources(sources, DummyFactory(), RetryConfig())

    assert output.shape[0] == 2
    assert set(output["source_name"]) == {"bio", "med"}


def test_write_outputs_writes_files_and_calls_storage(tmp_path) -> None:
    """Write outputs to disk and delegate table persistence to storage.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Asserts:
        Both Parquet and CSV are written (when enabled) and storage.write_table
        is called with the expected table name.
    """
    config = PipelineConfig(
        sources=[],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir=str(tmp_path), write_csv=True),
        transform=TransformConfig(),
        retry=RetryConfig(),
    )

    class DummyStorage(Storage):
        """Storage stub capturing write_table calls."""

        def __init__(self) -> None:
            self.calls = []

        def load_raw(self, df: pd.DataFrame) -> None:
            pass

        def read_raw(self) -> pd.DataFrame:
            pass

        def write_table(self, table_name: str, df: pd.DataFrame) -> None:
            self.calls.append((table_name, df.copy()))

    df = pd.DataFrame([{"doi": "10.1/abc", "metric": 1.0}])
    storage = DummyStorage()

    write_outputs(storage, config, df, "diff_features")

    assert (tmp_path / "diff_features.parquet").exists()
    assert (tmp_path / "diff_features.csv").exists()
    assert storage.calls[0][0] == "diff_features"


def test_run_pipeline_returns_zero_when_empty(monkeypatch) -> None:
    """Return a zero-count summary when extraction yields no rows.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to replace factories.

    Asserts:
        run_pipeline returns `{"raw_rows": 0, "diff_rows": 0}` when extraction
        returns an empty DataFrame.
    """
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
        """Extractor stub returning an empty DataFrame."""

        def fetch(self, source, retry_config):
            return pd.DataFrame()

    class DummyExtractorFactory:
        """ExtractorFactory stub returning DummyExtractor."""

        def create(self, source):
            return DummyExtractor()

    class DummyStorageFactory:
        """StorageFactory stub returning a placeholder object."""

        def create(self, storage):
            return object()

    class DummyTransformerFactory:
        """TransformerFactory stub returning a placeholder object."""

        def create(self, config):
            return object()

    monkeypatch.setattr("peer_elt.pipeline.ExtractorFactory", DummyExtractorFactory)
    monkeypatch.setattr("peer_elt.pipeline.StorageFactory", DummyStorageFactory)
    monkeypatch.setattr("peer_elt.pipeline.TransformerFactory", DummyTransformerFactory)

    result = run_pipeline(config)

    assert result == {"raw_rows": 0, "diff_rows": 0}


def test_cli_extract_prints_counts(monkeypatch, capsys) -> None:
    """Print JSON summary for the `extract` command.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to replace dependencies.
        capsys: Pytest capture fixture for stdout/stderr.

    Asserts:
        The CLI prints a JSON object containing `raw_rows`.
    """
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
        """ExtractorFactory stub used by the CLI."""

        def create(self, source):
            return object()

    class DummyStorage:
        """Storage stub used by the CLI."""

        def load_raw(self, df: pd.DataFrame) -> None:
            return None

    class DummyStorageFactory:
        """StorageFactory stub used by the CLI."""

        def create(self, storage):
            return DummyStorage()

    class DummyTransformerFactory:
        """TransformerFactory stub used by the CLI."""

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
