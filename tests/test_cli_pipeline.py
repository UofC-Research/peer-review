"""Tests for CLI JSON output and exit-code contracts.

These tests validate the behavior of :mod:`peer_elt.cli` without invoking a real
process. They call :func:`peer_elt.cli.main` directly with an ``argv`` list and
use pytest fixtures to capture output streams.

What is covered
---------------
Success paths
- ``run`` prints the pipeline result JSON to stdout.
- ``transform`` reads raw data, writes outputs, and prints a JSON count to stdout.

Failure paths / contracts
- Unexpected runtime exceptions are converted into an error JSON payload written
  to stderr and return a non-zero exit code (``1``).
- Argument/usage errors (argparse validation failures) produce a JSON error
  payload written to stderr and return exit code ``2``.
- By default, usage-error JSON includes ``"usage"`` but omits verbose ``"help"``.
  When ``--verbose-errors`` is supplied, the payload includes ``"help"`` as well.

Testing approach
----------------
- Dependencies are stubbed with ``monkeypatch`` (config loading, factories, and
  pipeline calls) to avoid network/DB work.
- Assertions focus on stable, observable outcomes: JSON payloads on stdout/stderr,
  exit codes, and whether key orchestration functions were invoked.
"""
import json

import pandas as pd

from peer_elt import cli
from peer_elt.config import (
    OutputConfig,
    PipelineConfig,
    RetryConfig,
    SourceConfig,
    StorageConfig,
    TransformConfig,
)


def _dummy_config() -> PipelineConfig:
    return PipelineConfig(
        sources=[
            SourceConfig(
                name="bio",
                server="biorxiv",
                date_from="2023-01-01",
                date_to="2023-01-02",
            )
        ],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir="data/out", write_csv=False),
        transform=TransformConfig(),
        retry=RetryConfig(),
    )


def test_cli_run_prints_pipeline_result(monkeypatch, capsys) -> None:
    config = _dummy_config()

    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "run_pipeline", lambda cfg: {"raw_rows": 2, "diff_rows": 1})

    cli.main(["--config", "config.yml", "run"])

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"raw_rows": 2, "diff_rows": 1}


def test_cli_run_uses_local_config_by_default(monkeypatch, capsys) -> None:
    config = _dummy_config()
    loaded_paths = []

    def _fake_load_config(path):
        loaded_paths.append(path)
        return config

    monkeypatch.setattr(cli, "load_config", _fake_load_config)
    monkeypatch.setattr(
        cli, "run_pipeline", lambda cfg: {"raw_rows": 0, "diff_rows": 0}
    )

    exit_code = cli.main(["run"])

    assert exit_code == 0
    assert loaded_paths == [cli.DEFAULT_CONFIG_PATH]
    assert json.loads(capsys.readouterr().out.strip()) == {
        "raw_rows": 0,
        "diff_rows": 0,
    }


def test_cli_run_accepts_explicit_config_path(monkeypatch) -> None:
    config = _dummy_config()
    loaded_paths = []

    def _fake_load_config(path):
        loaded_paths.append(path)
        return config

    monkeypatch.setattr(cli, "load_config", _fake_load_config)
    monkeypatch.setattr(
        cli, "run_pipeline", lambda cfg: {"raw_rows": 0, "diff_rows": 0}
    )

    exit_code = cli.main(["--config", "configs/prod.yml", "run"])

    assert exit_code == 0
    assert loaded_paths == ["configs/prod.yml"]


def test_cli_returns_error_json_when_default_local_config_missing(
    monkeypatch, capsys
) -> None:
    def _fake_load_config(path):
        raise FileNotFoundError(f"Config file does not exist: {path}")

    monkeypatch.setattr(cli, "load_config", _fake_load_config)

    exit_code = cli.main(["run"])

    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    payload = json.loads(captured.err.strip())

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["type"] == "FileNotFoundError"
    assert cli.DEFAULT_CONFIG_PATH in payload["error"]["message"]


def test_cli_returns_error_json_when_explicit_prod_config_missing(
    monkeypatch, capsys
) -> None:
    def _fake_load_config(path):
        raise FileNotFoundError(f"Config file does not exist: {path}")

    monkeypatch.setattr(cli, "load_config", _fake_load_config)

    exit_code = cli.main(["--config", "configs/prod.yml", "run"])

    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    payload = json.loads(captured.err.strip())

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["type"] == "FileNotFoundError"
    assert "configs/prod.yml" in payload["error"]["message"]


def test_cli_transform_reads_raw_writes_outputs_and_prints_diff_rows(monkeypatch, capsys) -> None:
    config = _dummy_config()

    class DummyStorage:
        def read_raw(self) -> pd.DataFrame:
            return pd.DataFrame([{"x": 1}, {"x": 2}])

    class DummyStorageFactory:
        def create(self, storage_config):
            return DummyStorage()

    class DummyTransformer:
        def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
            return pd.DataFrame([{"y": 10}])

    class DummyTransformerFactory:
        def create(self, pipeline_config):
            return DummyTransformer()

    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "StorageFactory", DummyStorageFactory)
    monkeypatch.setattr(cli, "TransformerFactory", DummyTransformerFactory)

    calls = {}

    def _fake_write_outputs(storage, cfg, df, name):
        calls["name"] = name
        calls["rows"] = int(df.shape[0])

    monkeypatch.setattr(cli, "write_outputs", _fake_write_outputs)

    cli.main(["--config", "config.yml", "transform"])

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["diff_rows"] == 1
    assert calls == {"name": "diff_features", "rows": 1}


def test_cli_run_prints_error_json_and_returns_nonzero_on_exception(monkeypatch, capsys) -> None:
    config = _dummy_config()

    monkeypatch.setattr(cli, "load_config", lambda path: config)

    def _boom(cfg):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(cli, "run_pipeline", _boom)

    exit_code = cli.main(["--config", "config.yml", "run"])

    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    payload = json.loads(captured.err.strip())

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["error"]["message"] == "kaboom"


def test_cli_argparse_error_prints_json_including_usage_and_returns_2(capsys) -> None:
    exit_code = cli.main(["--config", "config.yml"])  # missing subcommand

    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    payload = json.loads(captured.err.strip())

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["type"] == "UsageError"
    assert "command" in payload["error"]["message"].lower()

    assert "usage" in payload
    assert isinstance(payload["usage"], str)
    assert "extract" in payload["usage"]
    assert "run" in payload["usage"]

    assert "help" not in payload


def test_cli_argparse_error_with_verbose_errors_flag_includes_help(capsys) -> None:
    exit_code = cli.main(["--verbose-errors", "--config", "config.yml"])  # missing subcommand

    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    payload = json.loads(captured.err.strip())

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"]["type"] == "UsageError"

    assert "usage" in payload
    assert "help" in payload
    assert isinstance(payload["help"], str)
    assert "extract" in payload["help"]
    assert "transform" in payload["help"]
    assert "run" in payload["help"]
