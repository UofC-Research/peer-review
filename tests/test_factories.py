import pytest
from peer_elt.config import (
    OutputConfig,
    PipelineConfig,
    RetryConfig,
    SourceConfig,
    StorageConfig,
    TransformConfig,
)
from peer_elt.extract.registry import PreprintServerRegistry, RegistryExtractor
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.load.duckdb import DuckDBStorage
"""Tests for factory classes.

These tests verify that the factory layer constructs the correct concrete
implementations given configuration inputs (extractor, storage, transformer).
"""

import pytest
from peer_elt.config import (
    OutputConfig,
    PipelineConfig,
    RetryConfig,
    SourceConfig,
    StorageConfig,
    TransformConfig,
)
from peer_elt.extract.registry import PreprintServerRegistry, RegistryExtractor
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.transform.diff import DiffTransformer


def _pipeline_config() -> PipelineConfig:
    """Build a minimal PipelineConfig used by factory tests.

    Returns:
        A PipelineConfig instance with a DuckDB backend and diff transformer
        settings.
    """
    return PipelineConfig(
        sources=[SourceConfig(name="biorxiv", server="biorxiv", date_from="2023-01-01", date_to="2023-01-02")],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir="data/processed"),
        transform=TransformConfig(enable_pdf_diff=False, pdf_dir=None),
        retry=RetryConfig(),
    )


def test_extractor_factory_supported_sources() -> None:
    """ExtractorFactory should construct an extractor for supported servers."""
    factory = ExtractorFactory()
    extractor = factory.create(
        SourceConfig(
            name="biorxiv",
            server="biorxiv",
            date_from="2023-01-01",
            date_to="2023-01-02",
        )
    )
    assert isinstance(extractor, RegistryExtractor)


def test_extractor_factory_rejects_unsupported_sources() -> None:
    """ExtractorFactory should raise ValueError for unsupported servers."""
    registry = PreprintServerRegistry()
    factory = ExtractorFactory(registry=registry)

    with pytest.raises(ValueError, match="Unsupported source server"):
        factory.create(
            SourceConfig(
                name="unknown",
                server="unknown",
                date_from="2023-01-01",
                date_to="2023-01-02",
            )
        )


def test_storage_factory_duckdb() -> None:
    """StorageFactory should return DuckDBStorage for backend='duckdb'."""
    factory = StorageFactory()
    storage = factory.create(StorageConfig(backend="duckdb", duckdb_path=":memory:"))
    assert isinstance(storage, DuckDBStorage)


def test_transformer_factory_diff() -> None:
    """TransformerFactory should construct the default DiffTransformer."""
    factory = TransformerFactory()
    transformer = factory.create(_pipeline_config())
    assert isinstance(transformer, DiffTransformer)
