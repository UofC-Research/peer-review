from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine

from peer_elt.config import StorageConfig


def _engine(config: StorageConfig):
    if not config.postgres_url:
        raise ValueError("postgres_url is required for postgres backend")
    return create_engine(config.postgres_url, future=True)


def load_raw_postgres(config: StorageConfig, df: pd.DataFrame) -> None:
    if df.empty:
        return
    engine = _engine(config)
    with engine.begin() as conn:
        df.to_sql("raw_preprints", conn, if_exists="append", index=False)


def write_table_postgres(config: StorageConfig, table_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    engine = _engine(config)
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)


def read_raw_postgres(config: StorageConfig) -> pd.DataFrame:
    engine = _engine(config)
    return pd.read_sql("select * from raw_preprints", engine)
