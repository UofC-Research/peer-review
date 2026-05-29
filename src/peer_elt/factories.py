from __future__ import annotations

"""Factories for selecting extractors, storage backends, and transformers.

This module implements a small factory layer that converts configuration
objects into concrete implementations of the pipeline interfaces.
"""

from peer_elt.config import PipelineConfig, SourceConfig, StorageConfig
from peer_elt.extract.registry import (
    PreprintServerRegistry,
    RegistryExtractor,
    default_registry,
)
from peer_elt.interfaces import Extractor, Storage, Transformer
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.load.postgres import PostgresStorage
from peer_elt.transform.diff import DiffTransformer


class ExtractorFactory:
    """Create extractor implementations based on a configured source.

    Parameters
    ----------
    registry : peer_elt.extract.registry.PreprintServerRegistry | None, default=None
        Registry used to validate and dispatch supported preprint servers. If
        omitted, the default bioRxiv/medRxiv registry is used.
    """

    def __init__(self, registry: PreprintServerRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def create(self, source: SourceConfig) -> Extractor:
        """Create an extractor for the configured preprint server.

        Parameters
        ----------
        source : peer_elt.config.SourceConfig
            Source configuration containing the server slug to extract from.

        Returns
        -------
        peer_elt.interfaces.Extractor
            Extractor implementation for the configured preprint server.

        Raises
        ------
        ValueError
            If ``source.server`` is not registered as a supported server.
        """
        if not self._registry.has_server(source.server):
            raise ValueError(f"Unsupported source server: {source.server}")
        return RegistryExtractor(self._registry)


class StorageFactory:
    """Create storage backends based on storage configuration."""

    def create(self, config: StorageConfig) -> Storage:
        """Create a storage backend for ``config.backend``.

        Parameters
        ----------
        config : peer_elt.config.StorageConfig
            Storage configuration. The ``backend`` field selects the concrete
            implementation.

        Returns
        -------
        peer_elt.interfaces.Storage
            Storage backend implementation.

        Raises
        ------
        ValueError
            If ``config.backend`` is not supported by the factory.
        """
        if config.backend == "duckdb":
            return DuckDBStorage(config)
        if config.backend == "postgres":
            return PostgresStorage(config)
        raise ValueError(f"Unsupported backend: {config.backend}")


class TransformerFactory:
    """Create transformers based on the pipeline configuration."""

    def create(self, config: PipelineConfig) -> Transformer:
        """Create the configured transformer implementation.

        Parameters
        ----------
        config : peer_elt.config.PipelineConfig
            Pipeline configuration containing transform settings.

        Returns
        -------
        peer_elt.interfaces.Transformer
            Transformer implementation configured for the pipeline.
        """
        return DiffTransformer(
            enable_pdf_diff=config.transform.enable_pdf_diff,
            pdf_dir=config.transform.pdf_dir,
        )


__all__ = ["ExtractorFactory", "StorageFactory", "TransformerFactory"]
