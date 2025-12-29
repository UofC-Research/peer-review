from peer_elt.config import PipelineConfig, SourceConfig, StorageConfig, OutputConfig, TransformConfig
from peer_elt.extract.biorxiv import BiorxivApiExtractor
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.transform.diff import DiffTransformer


def _pipeline_config() -> PipelineConfig:
    return PipelineConfig(
        sources=[SourceConfig(name="biorxiv", server="biorxiv", date_from="2023-01-01", date_to="2023-01-02")],
        storage=StorageConfig(backend="duckdb", duckdb_path=":memory:"),
        output=OutputConfig(base_dir="data/processed"),
        transform=TransformConfig(enable_pdf_diff=False, pdf_dir=None),
    )


def test_extractor_factory_supported_sources() -> None:
    factory = ExtractorFactory()
    extractor = factory.create(
        SourceConfig(name="biorxiv", server="biorxiv", date_from="2023-01-01", date_to="2023-01-02"))
    assert isinstance(extractor, BiorxivApiExtractor)


def test_storage_factory_duckdb() -> None:
    factory = StorageFactory()
    storage = factory.create(StorageConfig(backend="duckdb", duckdb_path=":memory:"))
    assert isinstance(storage, DuckDBStorage)


def test_transformer_factory_diff() -> None:
    factory = TransformerFactory()
    transformer = factory.create(_pipeline_config())
    assert isinstance(transformer, DiffTransformer)
