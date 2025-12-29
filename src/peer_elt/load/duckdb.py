from __future__ import annotations

import pandas as pd
from peer_elt.config import StorageConfig
from peer_elt.interfaces import Storage

import duckdb


def _connect(config: StorageConfig) -> duckdb.DuckDBPyConnection:
    if not config.duckdb_path:
        raise ValueError("duckdb_path is required for duckdb backend")
    return duckdb.connect(config.duckdb_path)


def load_raw_duckdb(config: StorageConfig, df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect(config) as conn:
        conn.register("raw_df", df)
        conn.execute(
            "create table if not exists raw_preprints as select * from raw_df limit 0"
        )
        conn.execute("insert into raw_preprints select * from raw_df")


def write_table_duckdb(config: StorageConfig, table_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    with _connect(config) as conn:
        conn.register("out_df", df)
        conn.execute(
            f"create table if not exists {table_name} as select * from out_df limit 0"
        )
        conn.execute(f"insert into {table_name} select * from out_df")


def read_raw_duckdb(config: StorageConfig) -> pd.DataFrame:
    with _connect(config) as conn:
        return conn.execute("select * from raw_preprints").df()


class DuckDBStorage(Storage):
    def __init__(self, config: StorageConfig) -> None:
        self._config = config

    def load_raw(self, df: pd.DataFrame) -> None:
        load_raw_duckdb(self._config, df)

    def read_raw(self) -> pd.DataFrame:
        return read_raw_duckdb(self._config)

    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        write_table_duckdb(self._config, table_name, df)
