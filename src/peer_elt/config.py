from __future__ import annotations

"""Configuration models and YAML loader for the pipeline.

The config classes are dataclasses to make them explicit and easy to
validate and serialize. The loader expands environment variables in
storage settings to keep secrets out of committed files.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class SourceConfig:
    """Source metadata for a preprint server.

    Attributes:
        name: Friendly name for the source (used for tagging).
        server: API server slug (e.g., "biorxiv", "medrxiv").
        date_from: Inclusive start date in YYYY-MM-DD.
        date_to: Inclusive end date in YYYY-MM-DD.
    """
    name: str
    server: str
    date_from: str
    date_to: str


@dataclass(frozen=True)
class StorageConfig:
    """Storage backend configuration.

    Attributes:
        backend: "duckdb" or "postgres".
        duckdb_path: Path to a local DuckDB file, when using DuckDB.
        postgres_url: SQLAlchemy connection string for PostgreSQL.
    """
    backend: str
    duckdb_path: Optional[str] = None
    postgres_url: Optional[str] = None


@dataclass(frozen=True)
class OutputConfig:
    """Output file configuration.

    Attributes:
        base_dir: Base folder for Parquet/CSV outputs.
        write_csv: Whether to also emit CSV alongside Parquet.
    """
    base_dir: str
    write_csv: bool = False


@dataclass(frozen=True)
class TransformConfig:
    """Transform options for diff feature extraction.

    Attributes:
        enable_pdf_diff: Enable optional PDF similarity metrics.
        pdf_dir: Folder containing `preprint/` and `published/` PDFs.
    """
    enable_pdf_diff: bool = False
    pdf_dir: Optional[str] = None


@dataclass(frozen=True)
class RetryConfig:
    """Retry/backoff configuration for external API calls.

    Attributes:
        max_attempts: Total attempts before giving up.
        wait_min_seconds: Minimum backoff delay in seconds.
        wait_max_seconds: Maximum backoff delay in seconds.
        wait_multiplier: Exponential multiplier for backoff.
    """
    max_attempts: int = 5
    wait_min_seconds: int = 1
    wait_max_seconds: int = 60
    wait_multiplier: int = 1


@dataclass(frozen=True)
class PipelineConfig:
    """Top-level pipeline configuration.

    This combines sources, storage, output, and transform settings.
    """
    sources: list[SourceConfig]
    storage: StorageConfig
    output: OutputConfig
    transform: TransformConfig
    retry: RetryConfig


def _as_source_config(item: Dict[str, Any]) -> SourceConfig:
    return SourceConfig(
        name=item["name"],
        server=item["server"],
        date_from=item["date_from"],
        date_to=item["date_to"],
    )


def load_config(path: str | Path) -> PipelineConfig:
    """Load YAML configuration and expand env vars for storage targets.

    Args:
        path: Path to the YAML file.

    Returns:
        PipelineConfig: Parsed configuration.
    """
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    sources = [_as_source_config(item) for item in payload["sources"]]
    storage_payload = {
        key: os.path.expandvars(value) if isinstance(value, str) else value
        for key, value in payload["storage"].items()
    }
    storage = StorageConfig(**storage_payload)
    output = OutputConfig(**payload["output"])
    transform = TransformConfig(**payload.get("transform", {}))
    retry = RetryConfig(**payload.get("retry", {}))

    return PipelineConfig(
        sources=sources,
        storage=storage,
        output=output,
        transform=transform,
        retry=retry,
    )
