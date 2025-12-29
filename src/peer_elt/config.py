from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class SourceConfig:
    name: str
    server: str
    date_from: str
    date_to: str


@dataclass(frozen=True)
class StorageConfig:
    backend: str
    duckdb_path: Optional[str] = None
    postgres_url: Optional[str] = None


@dataclass(frozen=True)
class OutputConfig:
    base_dir: str
    write_csv: bool = False


@dataclass(frozen=True)
class TransformConfig:
    enable_pdf_diff: bool = False
    pdf_dir: Optional[str] = None


@dataclass(frozen=True)
class PipelineConfig:
    sources: list[SourceConfig]
    storage: StorageConfig
    output: OutputConfig
    transform: TransformConfig


def _as_source_config(item: Dict[str, Any]) -> SourceConfig:
    return SourceConfig(
        name=item["name"],
        server=item["server"],
        date_from=item["date_from"],
        date_to=item["date_to"],
    )


def load_config(path: str | Path) -> PipelineConfig:
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

    return PipelineConfig(
        sources=sources,
        storage=storage,
        output=output,
        transform=transform,
    )
