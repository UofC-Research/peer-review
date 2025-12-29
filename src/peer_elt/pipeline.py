from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import pandas as pd
from peer_elt.config import PipelineConfig, SourceConfig
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.interfaces import Extractor, Storage, Transformer


def extract_sources(
        sources: Iterable[SourceConfig],
        extractor_factory: ExtractorFactory,
) -> pd.DataFrame:
    frames = []
    for source in sources:
        extractor = extractor_factory.create(source)
        frame = extractor.fetch(source)
        frame["source_name"] = source.name
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_raw(storage: Storage, raw_df: pd.DataFrame) -> None:
    storage.load_raw(raw_df)


def transform(transformer: Transformer, raw_df: pd.DataFrame) -> pd.DataFrame:
    return transformer.transform(raw_df)


def write_outputs(storage: Storage, config: PipelineConfig, df: pd.DataFrame, name: str) -> None:
    output_dir = Path(config.output.base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = output_dir / f"{name}.parquet"
    df.to_parquet(parquet_path, index=False)

    if config.output.write_csv:
        csv_path = output_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False)

    storage.write_table(name, df)


def run_pipeline(config: PipelineConfig) -> dict:
    extractor_factory = ExtractorFactory()
    storage_factory = StorageFactory()
    transformer_factory = TransformerFactory()

    storage = storage_factory.create(config.storage)
    transformer = transformer_factory.create(config)

    raw_df = extract_sources(config.sources, extractor_factory)
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
