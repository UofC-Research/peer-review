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
from peer_elt.config import PipelineConfig, SourceConfig
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.interfaces import Storage, Transformer


def extract_sources(
        sources: Iterable[SourceConfig],
        extractor_factory: ExtractorFactory,
        retry_config,
) -> pd.DataFrame:
    """Pull raw metadata from each source and combine into one frame.

    Args:
        sources: Iterable[peer_elt.config.SourceConfig]
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
