from __future__ import annotations

"""PostgreSQL-backed storage implementation for the pipeline."""

import pandas as pd
from peer_elt.config import StorageConfig
from peer_elt.interfaces import Storage
from sqlalchemy import create_engine


def _engine(config: StorageConfig):
    """Create a SQLAlchemy engine for PostgreSQL.

    Args:
        config: StorageConfig with a postgres_url.
    """
    if not config.postgres_url:
        raise ValueError("postgres_url is required for postgres backend")
    return create_engine(config.postgres_url, future=True)


def load_raw_postgres(config: StorageConfig, df: pd.DataFrame) -> None:
    """Append raw preprint metadata to PostgreSQL."""
    if df.empty:
        return
    engine = _engine(config)
    with engine.begin() as conn:
        df.to_sql("raw_preprints", conn, if_exists="append", index=False)


def write_table_postgres(config: StorageConfig, table_name: str, df: pd.DataFrame) -> None:
    """Append a named table to PostgreSQL."""
    if df.empty:
        return
    engine = _engine(config)
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)


def read_raw_postgres(config: StorageConfig) -> pd.DataFrame:
    """Read raw preprint metadata from PostgreSQL."""
    engine = _engine(config)
    return pd.read_sql("select * from raw_preprints", engine)


class PostgresStorage(Storage):
    """PostgreSQL-backed storage implementation."""

    def __init__(self, config: StorageConfig) -> None:
        """Initialize the storage with a PostgreSQL config."""
        self._config = config

    def load_raw(self, df: pd.DataFrame) -> None:
        load_raw_postgres(self._config, df)

    def read_raw(self) -> pd.DataFrame:
        return read_raw_postgres(self._config)

    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        write_table_postgres(self._config, table_name, df)
