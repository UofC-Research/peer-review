from __future__ import annotations

"""peer_elt.config

Configuration schema + YAML loader for the ELT pipeline.

This module is the *schema boundary* between YAML files and runtime objects used
by the pipeline and CLI.

It provides:
- Frozen dataclasses describing supported configuration sections.
- `load_config()` which loads YAML, validates structure, expands environment
  variables in storage settings, and returns a `PipelineConfig`.

YAML contract (high level)
--------------------------
Required top-level keys
- `sources`: list of mappings
- `storage`: mapping
- `output`: mapping

Optional top-level keys
- `transform`: mapping (defaults to `{}`)
- `retry`: mapping (defaults to `{}`)

Environment variables
---------------------
Only values under the `storage` block are expanded using `os.path.expandvars`.
After expansion, any remaining `${VARNAME}` placeholders are treated as errors.

Path handling
-------------
If `output.base_dir` is a relative path, it is resolved relative to the directory
containing the config file. Absolute paths are preserved.

Notes
-----
- Date values are treated as strings. Parsing/validation is left to downstream
  components if needed.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class SourceConfig:
    """Configuration for one extraction source.

    Parameters
    ----------
    name:
        Friendly label for the source (used for tagging).
    server:
        Server identifier used by extractors (e.g., "biorxiv", "medrxiv").
    date_from:
        Inclusive start date string (e.g., "YYYY-MM-DD").
    date_to:
        Inclusive end date string (e.g., "YYYY-MM-DD").
    """

    name: str
    server: str
    date_from: str
    date_to: str


@dataclass(frozen=True)
class StorageConfig:
    """Storage backend configuration.

    The loader enforces backend-specific required keys for known backends:
    - `backend == "duckdb"`   requires `duckdb_path`
    - `backend == "postgres"` requires `postgres_url`

    Unknown backends are allowed; extra backend-specific keys are stored in `options`.

    Parameters
    ----------
    backend:
        Backend identifier (e.g., "duckdb", "postgres", "sqlite").
    duckdb_path:
        DuckDB database path (or ":memory:") for backend "duckdb".
    postgres_url:
        Postgres connection string for backend "postgres" (often `${POSTGRES_URL}`).
    options:
        Extra backend-specific settings preserved from the YAML `storage` block.
    """

    backend: str
    duckdb_path: Optional[str] = None
    postgres_url: Optional[str] = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutputConfig:
    """Output file settings.

    Parameters
    ----------
    base_dir:
        Base directory where outputs will be written. `load_config()` resolves a
        relative path against the directory containing the YAML file.
    write_csv:
        If True, emit CSV alongside Parquet outputs.
    """

    base_dir: str
    write_csv: bool = False


@dataclass(frozen=True)
class TransformConfig:
    """Transformation / feature-extraction settings.

    Parameters
    ----------
    enable_pdf_diff:
        Toggle optional PDF-diff features.
    pdf_dir:
        Directory holding PDFs (exact layout is transformer-dependent).
    """

    enable_pdf_diff: bool = False
    pdf_dir: Optional[str] = None


@dataclass(frozen=True)
class RetryConfig:
    """Retry/backoff settings for network calls.

    Parameters
    ----------
    max_attempts:
        Total attempts per request (initial attempt included).
    wait_min_seconds:
        Minimum backoff delay (seconds).
    wait_max_seconds:
        Maximum backoff delay (seconds).
    wait_multiplier:
        Exponential backoff multiplier.
    """

    max_attempts: int = 5
    wait_min_seconds: int = 1
    wait_max_seconds: int = 60
    wait_multiplier: int = 1


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level configuration returned by `load_config()`."""

    sources: list[SourceConfig]
    storage: StorageConfig
    output: OutputConfig
    transform: TransformConfig
    retry: RetryConfig


_ENV_VAR_PATTERN = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")


def load_config(path: str | Path) -> PipelineConfig:
    """Load and validate a YAML config file.

    Parameters
    ----------
    path:
        Path to the YAML config file.

    Returns
    -------
    PipelineConfig
        Parsed, immutable configuration object.

    Raises
    ------
    ValueError
        If the YAML file is empty, or if a storage value still contains an
        unexpanded `${VARNAME}` placeholder after expansion.
    TypeError
        If the YAML structure is not the expected shape.
    KeyError
        If required keys are missing (including backend-specific required keys).
    """
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    if payload is None:
        raise ValueError(f"Empty YAML config: {config_path}")
    if not isinstance(payload, dict):
        raise TypeError(
            f"Top-level YAML config must be a mapping/dict, got: {type(payload).__name__}"
        )

    required_top_level_keys = ("sources", "storage", "output")
    for key in required_top_level_keys:
        if key not in payload:
            raise KeyError(f"Top-level config missing required key: {key}")

    sources_payload = payload["sources"]
    if not isinstance(sources_payload, list):
        raise TypeError(f"`sources` must be a list, got: {type(sources_payload).__name__}")

    storage_block = payload["storage"]
    if not isinstance(storage_block, dict):
        raise TypeError(f"`storage` must be a mapping/dict, got: {type(storage_block).__name__}")

    output_block = payload["output"]
    if not isinstance(output_block, dict):
        raise TypeError(f"`output` must be a mapping/dict, got: {type(output_block).__name__}")

    base_dir_value = output_block.get("base_dir")
    if isinstance(base_dir_value, str):
        base_dir_path = Path(base_dir_value).expanduser()
        if not base_dir_path.is_absolute():
            base_dir_path = (config_path.parent / base_dir_path).resolve()
        output_block = {**output_block, "base_dir": str(base_dir_path)}

    transform_block = payload.get("transform", {})
    if transform_block is None:
        transform_block = {}
    if not isinstance(transform_block, dict):
        raise TypeError(f"`transform` must be a mapping/dict, got: {type(transform_block).__name__}")

    retry_block = payload.get("retry", {})
    if retry_block is None:
        retry_block = {}
    if not isinstance(retry_block, dict):
        raise TypeError(f"`retry` must be a mapping/dict, got: {type(retry_block).__name__}")

    for idx, item in enumerate(sources_payload):
        if not isinstance(item, dict):
            raise TypeError(
                "Each item in `sources` must be a mapping/dict; "
                f"item {idx} is {type(item).__name__}"
            )

    sources: list[SourceConfig] = []
    for idx, item in enumerate(sources_payload):
        try:
            sources.append(
                SourceConfig(
                    name=item["name"],
                    server=item["server"],
                    date_from=item["date_from"],
                    date_to=item["date_to"],
                )
            )
        except KeyError as exc:
            missing = exc.args[0] if exc.args else "<unknown>"
            raise KeyError(f"Source item {idx} missing required key: {missing}") from exc

    if "backend" not in storage_block:
        raise KeyError("Storage block missing required key: backend")

    backend = storage_block.get("backend")
    if backend == "duckdb" and "duckdb_path" not in storage_block:
        raise KeyError("Storage backend 'duckdb' requires key: duckdb_path")
    if backend == "postgres" and "postgres_url" not in storage_block:
        raise KeyError("Storage backend 'postgres' requires key: postgres_url")

    storage_payload = {
        k: os.path.expandvars(v) if isinstance(v, str) else v for k, v in storage_block.items()
    }

    for key, value in storage_payload.items():
        if isinstance(value, str) and _ENV_VAR_PATTERN.search(value):
            raise ValueError(f"Unexpanded environment variable in storage.{key}")

    known_keys = {"backend", "duckdb_path", "postgres_url"}
    options = {k: v for k, v in storage_payload.items() if k not in known_keys}

    storage = StorageConfig(
        backend=storage_payload["backend"],
        duckdb_path=storage_payload.get("duckdb_path"),
        postgres_url=storage_payload.get("postgres_url"),
        options=options,
    )

    output = OutputConfig(**output_block)
    transform = TransformConfig(**transform_block)
    retry = RetryConfig(**retry_block)

    return PipelineConfig(
        sources=sources,
        storage=storage,
        output=output,
        transform=transform,
        retry=retry,
    )
