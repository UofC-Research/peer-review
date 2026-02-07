from __future__ import annotations

"""Pipeline orchestration for extract, load, transform, and write steps.

This module keeps the execution sequence explicit and composes the extractor,
storage, and transformer implementations via factories.

The functions are intentionally small and linear so the pipeline can be run
either end-to-end (:func:`run_pipeline`) or stage-by-stage (e.g.,
:func:`extract_sources` then :func:`transform`).
"""

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import pandas as pd
# from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.config import PipelineConfig, SourceConfig, StorageConfig
from peer_elt.extract.registry import PreprintServerRegistry, RegistryExtractor, default_registry
from peer_elt.interfaces import Extractor, Storage, Transformer
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.load.postgres import PostgresStorage
from peer_elt.transform.diff import DiffTransformer

def extract_sources(
    sources: Iterable[SourceConfig],
    extractor_factory: ExtractorFactory,
    retry_config,
) -> pd.DataFrame:
    """Extract raw metadata from multiple configured sources.

    Parameters
    ----------
    sources : Iterable[peer_elt.config.SourceConfig]
        Source configurations to extract from.
    extractor_factory : peer_elt.factories.ExtractorFactory
        Factory used to construct an extractor for each source.
    retry_config
        Retry/backoff configuration passed to extractors for external API calls
        (typically a ``RetryConfig``).

    Returns
    -------
    pandas.DataFrame
        Combined raw metadata for all sources. If no sources produce data, an
        empty DataFrame is returned.

    Notes
    -----
    This function adds a ``source_name`` column to each extracted frame based on
    :attr:`peer_elt.config.SourceConfig.name`.
    """
    frames = []
    for source in sources:
        extractor = extractor_factory.create(source)
        frame = extractor.fetch(source, retry_config)
        frame["source_name"] = source.name
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_raw(storage: Storage, raw_df: pd.DataFrame) -> None:
    """Persist raw extracted metadata to the configured storage backend.

    Parameters
    ----------
    storage : peer_elt.interfaces.Storage
        Storage backend implementation.
    raw_df : pandas.DataFrame
        Raw metadata to persist.

    Returns
    -------
    None
    """
    storage.load_raw(raw_df)


def transform(transformer: Transformer, raw_df: pd.DataFrame) -> pd.DataFrame:
    """Compute analysis-ready features from raw metadata.

    Parameters
    ----------
    transformer : peer_elt.interfaces.Transformer
        Transformer implementation used to compute derived features.
    raw_df : pandas.DataFrame
        Raw metadata dataframe.

    Returns
    -------
    pandas.DataFrame
        Derived feature table produced by the transformer.
    """
    return transformer.transform(raw_df)


def write_outputs(storage: Storage, config: PipelineConfig, df: pd.DataFrame, name: str) -> None:
    """Write outputs to disk and to the configured storage backend.

    This function always writes a Parquet file to ``config.output.base_dir`` and
    optionally writes a CSV file depending on ``config.output.write_csv``. It
    also persists the same dataframe via :meth:`peer_elt.interfaces.Storage.write_table`.

    Parameters
    ----------
    storage : peer_elt.interfaces.Storage
        Storage backend implementation used for persisting named tables.
    config : peer_elt.config.PipelineConfig
        Pipeline configuration (used for output path and CSV toggle).
    df : pandas.DataFrame
        Output dataframe to persist.
    name : str
        Logical output name used for file naming and as the storage table name.

    Returns
    -------
    None
    """
    output_dir = Path(config.output.base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = output_dir / f"{name}.parquet"
    df.to_parquet(parquet_path, index=False)

    if config.output.write_csv:
        csv_path = output_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False)

    storage.write_table(name, df)


def run_pipeline(config: PipelineConfig) -> dict:
    """Run extract, load, transform, and write stages end-to-end.

    Parameters
    ----------
    config : peer_elt.config.PipelineConfig
        Pipeline configuration.

    Returns
    -------
    dict
        Summary dictionary including:

        - ``raw_rows``: number of extracted raw rows
        - ``diff_rows``: number of derived feature rows
        - ``config``: serialized config snapshot (via :func:`dataclasses.asdict`)

        If extraction yields no data, returns ``{"raw_rows": 0, "diff_rows": 0}``.

    Notes
    -----
    This function constructs factories internally and wires together the pipeline
    stages using the configured implementations.
    """
    extractor_factory = ExtractorFactory()
    storage_factory = StorageFactory()
    transformer_factory = TransformerFactory()

    storage = storage_factory.create(config.storage)
    transformer = transformer_factory.create(config)

    raw_df = extract_sources(config.sources, extractor_factory, config.retry)
    if raw_df.empty:
        return {"raw_rows": 0, "diff_rows": 0}

    load_raw(storage, raw_df)
    diff_df = transform(transformer, raw_df)
    write_outputs(storage, config, diff_df, "diff_features")

    return {
        "raw_rows": int(raw_df.shape[0]),
        "diff_rows": int(diff_df.shape[0]),
        "config": asdict(config),
    }

"""Factories for selecting extractors, storage backends, and transformers.

This module implements a small *factory layer* that converts configuration
objects into concrete implementations of the pipeline interfaces.

The goal is to keep selection logic (e.g., "which backend?") out of the pipeline
or orchestration code so that:

- the rest of the code depends on stable interfaces,
- new implementations can be added in one place,
- configuration-driven wiring stays explicit and testable.

Notes
-----
Factories here return objects implementing interfaces from
:mod:`peer_elt.interfaces`:

- :class:`peer_elt.interfaces.Extractor`
- :class:`peer_elt.interfaces.Storage`
- :class:`peer_elt.interfaces.Transformer`
"""

class ExtractorFactory:
    """Create extractor implementations based on a configured source.

    The factory uses a :class:`peer_elt.extract.registry.PreprintServerRegistry`
    to validate that a requested server is supported.

    Parameters
    ----------
    registry : peer_elt.extract.registry.PreprintServerRegistry | None, default=None
        Registry used to look up/validate available preprint servers. If not
        provided, :func:`peer_elt.extract.registry.default_registry` is used.

    Notes
    -----
    The returned extractor is currently a :class:`peer_elt.extract.registry.RegistryExtractor`,
    which delegates to the configured registry for server-specific behavior.

    The selection check is performed on ``source.server``; if unsupported,
    :meth:`create` raises.
    """

    def __init__(self, registry: PreprintServerRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def create(self, source: SourceConfig) -> Extractor:
        """Create an extractor for the given source.

        Parameters
        ----------
        source : peer_elt.config.SourceConfig
            Source metadata including the ``server`` slug.

        Returns
        -------
        peer_elt.interfaces.Extractor
            Extractor instance capable of pulling raw metadata for the requested
            preprint server.

        Raises
        ------
        ValueError
            If ``source.server`` is not present in the registry.
        """
        if not self._registry.has_server(source.server):
            raise ValueError(f"Unsupported source server: {source.server}")
        return RegistryExtractor(self._registry)


class StorageFactory:
    """Create storage backends based on storage configuration.

    Supported backends are selected via :attr:`peer_elt.config.StorageConfig.backend`.

    Notes
    -----
    Supported values for ``backend``:

    - ``"duckdb"`` -> :class:`peer_elt.load.duckdb.DuckDBStorage`
    - ``"postgres"`` -> :class:`peer_elt.load.postgres.PostgresStorage`
    """

    def create(self, config: StorageConfig) -> Storage:
        """Create a storage backend.

        Parameters
        ----------
        config : peer_elt.config.StorageConfig
            Storage configuration. The ``backend`` field selects the concrete
            implementation.

        Returns
        -------
        peer_elt.interfaces.Storage
            Storage implementation for reading/writing raw and derived datasets.

        Raises
        ------
        ValueError
            If ``config.backend`` is not a supported backend identifier.
        """
        if config.backend == "duckdb":
            return DuckDBStorage(config)
        if config.backend == "postgres":
            return PostgresStorage(config)
        raise ValueError(f"Unsupported backend: {config.backend}")


class TransformerFactory:
    """Create transformers based on the pipeline configuration.

    Notes
    -----
    The current implementation always returns :class:`peer_elt.transform.diff.DiffTransformer`.
    Configuration flags in ``config.transform`` control optional behavior (e.g.,
    enabling PDF-based similarity features).
    """

    def create(self, config: PipelineConfig) -> Transformer:
        """Create a transformer for the configured pipeline.

        Parameters
        ----------
        config : peer_elt.config.PipelineConfig
            Pipeline configuration. Transformer-related options are read from the
            ``transform`` block.

        Returns
        -------
        peer_elt.interfaces.Transformer
            Transformer instance used to convert raw extracted records into
            derived feature datasets.
        """
        return DiffTransformer(
            enable_pdf_diff=config.transform.enable_pdf_diff,
            pdf_dir=config.transform.pdf_dir,
        )
