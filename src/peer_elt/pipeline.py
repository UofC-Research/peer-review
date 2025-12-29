from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import pandas as pd

from peer_elt.config import PipelineConfig, SourceConfig
from peer_elt.extract.biorxiv import fetch_preprints
from peer_elt.load.duckdb import load_raw_duckdb, write_table_duckdb
from peer_elt.load.postgres import load_raw_postgres, write_table_postgres
from peer_elt.transform.diff import build_diff_features


def extract_sources(sources: Iterable[SourceConfig]) -> pd.DataFrame:
    frames = []
    for source in sources:
        frame = fetch_preprints(
            server=source.server,
            date_from=source.date_from,
            date_to=source.date_to,
        )
        frame["source_name"] = source.name
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_raw(config: PipelineConfig, raw_df: pd.DataFrame) -> None:
    if config.storage.backend == "duckdb":
        load_raw_duckdb(config.storage, raw_df)
    elif config.storage.backend == "postgres":
        load_raw_postgres(config.storage, raw_df)
    else:
        raise ValueError(f"Unsupported backend: {config.storage.backend}")


def transform(config: PipelineConfig, raw_df: pd.DataFrame) -> pd.DataFrame:
    return build_diff_features(
        raw_df,
        enable_pdf_diff=config.transform.enable_pdf_diff,
        pdf_dir=config.transform.pdf_dir,
    )


def write_outputs(config: PipelineConfig, df: pd.DataFrame, name: str) -> None:
    output_dir = Path(config.output.base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = output_dir / f"{name}.parquet"
    df.to_parquet(parquet_path, index=False)

    if config.output.write_csv:
        csv_path = output_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False)

    if config.storage.backend == "duckdb":
        write_table_duckdb(config.storage, name, df)
    elif config.storage.backend == "postgres":
        write_table_postgres(config.storage, name, df)


def run_pipeline(config: PipelineConfig) -> dict:
    raw_df = extract_sources(config.sources)
    if raw_df.empty:
        return {"raw_rows": 0, "diff_rows": 0}

    load_raw(config, raw_df)
    diff_df = transform(config, raw_df)
    write_outputs(config, diff_df, "diff_features")

    return {
        "raw_rows": int(raw_df.shape[0]),
        "diff_rows": int(diff_df.shape[0]),
        "config": asdict(config),
    }
