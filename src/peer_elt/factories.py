from __future__ import annotations

"""Factories for selecting extractors, storage backends, and transformers.

The factory layer centralizes selection logic so the rest of the
pipeline can depend on stable interfaces.
"""

from peer_elt.config import PipelineConfig, SourceConfig, StorageConfig
from peer_elt.extract.registry import PreprintServerRegistry, RegistryExtractor, default_registry
from peer_elt.interfaces import Extractor, Storage, Transformer
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.load.postgres import PostgresStorage
from peer_elt.transform.diff import DiffTransformer


class ExtractorFactory:
    """Selects extractor implementations based on source metadata.

    This supports bioRxiv and medRxiv via the same API client.
    """

    def __init__(self, registry: PreprintServerRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def create(self, source: SourceConfig) -> Extractor:
        if not self._registry.has_server(source.server):
            raise ValueError(f"Unsupported source server: {source.server}")
        return RegistryExtractor(self._registry)


class StorageFactory:
    """Selects storage backends based on config.

    Current backends: DuckDB and PostgreSQL.
    """

    def create(self, config: StorageConfig) -> Storage:
        if config.backend == "duckdb":
            return DuckDBStorage(config)
        if config.backend == "postgres":
            return PostgresStorage(config)
        raise ValueError(f"Unsupported backend: {config.backend}")


class TransformerFactory:
    """Selects transform pipelines based on config.

    The default transformer computes text and PDF similarity metrics.
    """

    def create(self, config: PipelineConfig) -> Transformer:
        return DiffTransformer(
            enable_pdf_diff=config.transform.enable_pdf_diff,
            pdf_dir=config.transform.pdf_dir,
        )
