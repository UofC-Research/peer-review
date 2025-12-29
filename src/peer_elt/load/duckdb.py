from __future__ import annotations

from typing import Optional

import duckdb
import pandas as pd

from peer_elt.config import StorageConfig


def _connect(config: StorageConfig) -> duckdb.DuckDBPyConnection:
    if not config.duckdb_path:
        raise ValueError("duckdb_path is required for duckdb backend")
    return duckdb.connect(config.duckdb_path)


def load_raw_duckdb(config: StorageConfig, df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect(config) as conn:
        conn.register("raw_df", df)
        conn.execute("create table if not exists raw_preprints as select * from raw_df")
        conn.execute("insert into raw_preprints select * from raw_df")


def write_table_duckdb(config: StorageConfig, table_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect(config) as conn:
        conn.register("out_df", df)
        conn.execute(f"create table if not exists {table_name} as select * from out_df")
        conn.execute(f"insert into {table_name} select * from out_df")


def read_raw_duckdb(config: StorageConfig) -> pd.DataFrame:
    with _connect(config) as conn:
        return conn.execute("select * from raw_preprints").df()
