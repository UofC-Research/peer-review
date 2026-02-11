from __future__ import annotations

"""Configuration models and YAML loader for the ELT pipeline.

This module defines *immutable* (frozen) dataclass models representing the
pipeline configuration, plus a loader for reading a YAML file into those models.

Why dataclasses?
----------------
- They provide an explicit schema (fields + types) that is easy to reason about.
- They are easy to serialize/debug (repr) and to validate at boundaries.

Environment-variable expansion
------------------------------
When loading the YAML, **string values** inside the ``storage`` block are passed
through :func:`os.path.expandvars`. This allows you to keep secrets out of
committed config files by using environment variables, e.g.::

    storage:
      backend: postgres
      postgres_url: ${POSTGRES_URL}

Example YAML
------------
A minimal DuckDB + Parquet config might look like::

    sources:
      - name: biorxiv-jan
        server: biorxiv
        date_from: "2023-01-01"
        date_to: "2023-01-31"

    storage:
      backend: duckdb
      duckdb_path: "data/peer.duckdb"

    output:
      base_dir: "data/out"
      write_csv: false

    transform:
      enable_pdf_diff: false
      pdf_dir: null

    retry:
      max_attempts: 5
      wait_min_seconds: 1
      wait_max_seconds: 60
      wait_multiplier: 1

Notes
-----
- This loader assumes the YAML has the expected top-level keys (``sources``,
  ``storage``, ``output``). Optional keys: ``transform`` and ``retry``.
- Date fields are stored as strings (YYYY-MM-DD). Parsing/validation can be
  performed by downstream components if needed.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# ... existing code ...


@dataclass(frozen=True)
class SourceConfig:
    """Source metadata for a preprint server.

    Each entry in the YAML ``sources`` list becomes one :class:`SourceConfig`.

    Attributes
    ----------
    name : str
        Friendly name for the source (often used for tagging/labeling).
    server : str
        API server slug (e.g., ``"biorxiv"``, ``"medrxiv"``).
    date_from : str
        Inclusive start date in ``YYYY-MM-DD`` format.
    date_to : str
        Inclusive end date in ``YYYY-MM-DD`` format.
    """

    name: str
    server: str
    date_from: str
    date_to: str


@dataclass(frozen=True)
class StorageConfig:
    """Storage backend configuration.

    Exactly which fields are required depends on ``backend``.

    Attributes
    ----------
    backend : str
        Storage backend identifier. Expected values: ``"duckdb"`` or
        ``"postgres"``.
    duckdb_path : str | None, default=None
        Path to a local DuckDB database file when using DuckDB.
    postgres_url : str | None, default=None
        SQLAlchemy connection string when using PostgreSQL. Environment variables
        may be used in YAML and are expanded at load time.
    """

    backend: str
    duckdb_path: Optional[str] = None
    postgres_url: Optional[str] = None


@dataclass(frozen=True)
class OutputConfig:
    """Output file configuration.

    Attributes
    ----------
    base_dir : str
        Base folder for outputs (e.g., Parquet and optionally CSV).
    write_csv : bool, default=False
        If True, also emit CSV alongside Parquet outputs.
    """

    base_dir: str
    write_csv: bool = False


@dataclass(frozen=True)
class TransformConfig:
    """Transform options for downstream feature extraction.

    Attributes
    ----------
    enable_pdf_diff : bool, default=False
        Enable optional PDF similarity metrics. When False, PDF-related settings
        may be ignored by transformers.
    pdf_dir : str | None, default=None
        Folder containing subfolders like ``preprint/`` and ``published/`` (exact
        layout depends on the transformer).
    """

    enable_pdf_diff: bool = False
    pdf_dir: Optional[str] = None


@dataclass(frozen=True)
class RetryConfig:
    """Retry/backoff configuration for external API calls.

    This configuration is intended for extractors or any networked component.

    Attributes
    ----------
    max_attempts : int, default=5
        Total attempts before giving up (initial try included).
    wait_min_seconds : int, default=1
        Minimum backoff delay in seconds.
    wait_max_seconds : int, default=60
        Maximum backoff delay in seconds.
    wait_multiplier : int, default=1
        Exponential multiplier for backoff growth.
    """

    max_attempts: int = 5
    wait_min_seconds: int = 1
    wait_max_seconds: int = 60
    wait_multiplier: int = 1


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level pipeline configuration object.

    Instances of this class are produced by :func:`load_config` and typically
    passed into the pipeline entrypoints.

    Attributes
    ----------
    sources : list[SourceConfig]
        List of data sources to extract from.
    storage : StorageConfig
        Storage backend settings (DuckDB or PostgreSQL).
    output : OutputConfig
        Output settings for writing derived datasets.
    transform : TransformConfig
        Transformation/feature extraction settings.
    retry : RetryConfig
        Retry/backoff settings for external API calls.
    """

    sources: list[SourceConfig]
    storage: StorageConfig
    output: OutputConfig
    transform: TransformConfig
    retry: RetryConfig


def _as_source_config(item: Dict[str, Any]) -> SourceConfig:
    """Convert a raw YAML mapping into a :class:`SourceConfig`.

    Parameters
    ----------
    item : dict[str, Any]
        Mapping with keys ``name``, ``server``, ``date_from``, ``date_to``.

    Returns
    -------
    SourceConfig
        Parsed source configuration.

    Raises
    ------
    KeyError
        If required keys are missing.
    TypeError
        If ``item`` is not a mapping-like object.
    """
    return SourceConfig(
        name=item["name"],
        server=item["server"],
        date_from=item["date_from"],
        date_to=item["date_to"],
    )


def load_config(path: str | Path) -> PipelineConfig:
    """Load a YAML configuration file into a :class:`PipelineConfig`."""
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    if payload is None:
        raise ValueError(f"Empty YAML config: {config_path}")
    if not isinstance(payload, dict):
        raise TypeError(
            f"Top-level YAML config must be a mapping/dict, got: {type(payload).__name__}"
        )

    sources_payload = payload["sources"]
    if not isinstance(sources_payload, list):
        raise TypeError(f"`sources` must be a list, got: {type(sources_payload).__name__}")

    storage_block = payload["storage"]
    if not isinstance(storage_block, dict):
        raise TypeError(f"`storage` must be a mapping/dict, got: {type(storage_block).__name__}")

    output_block = payload["output"]
    if not isinstance(output_block, dict):
        raise TypeError(f"`output` must be a mapping/dict, got: {type(output_block).__name__}")

    for idx, item in enumerate(sources_payload):
        if not isinstance(item, dict):
            raise TypeError(
                "Each item in `sources` must be a mapping/dict; "
                f"item {idx} is {type(item).__name__}"
            )

    sources = []
    for idx, item in enumerate(sources_payload):
        try:
            sources.append(_as_source_config(item))
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
        key: os.path.expandvars(value) if isinstance(value, str) else value
        for key, value in storage_block.items()
    }
    storage = StorageConfig(**storage_payload)
    output = OutputConfig(**output_block)
    transform = TransformConfig(**payload.get("transform", {}))
    retry = RetryConfig(**payload.get("retry", {}))

    return PipelineConfig(
        sources=sources,
        storage=storage,
        output=output,
        transform=transform,
        retry=retry,
    )
