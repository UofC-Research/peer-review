from __future__ import annotations

from peer_elt.config import PipelineConfig, SourceConfig, StorageConfig
from peer_elt.extract.biorxiv import BiorxivApiExtractor
from peer_elt.interfaces import Extractor, Storage, Transformer
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.load.postgres import PostgresStorage
from peer_elt.transform.diff import DiffTransformer


class ExtractorFactory:
    _supported = {"biorxiv", "medrxiv"}

    def create(self, source: SourceConfig) -> Extractor:
        if source.server not in self._supported:
            raise ValueError(f"Unsupported source server: {source.server}")
        return BiorxivApiExtractor()


class StorageFactory:
    def create(self, config: StorageConfig) -> Storage:
        if config.backend == "duckdb":
            return DuckDBStorage(config)
        if config.backend == "postgres":
            return PostgresStorage(config)
        raise ValueError(f"Unsupported backend: {config.backend}")


class TransformerFactory:
    def create(self, config: PipelineConfig) -> Transformer:
        return DiffTransformer(
            enable_pdf_diff=config.transform.enable_pdf_diff,
            pdf_dir=config.transform.pdf_dir,
        )
