from __future__ import annotations

"""PostgreSQL-backed storage implementation.

This module provides a PostgreSQL implementation of the pipeline storage
interface (:class:`peer_elt.interfaces.Storage`) using SQLAlchemy + pandas.

Tables
------
raw_preprints
    Raw extracted metadata appended via :func:`load_raw_postgres`.

{name}
    Named output tables appended via :func:`write_table_postgres`, where ``name``
    is the ``table_name`` argument (e.g., ``"diff_features"``).

Notes
-----
- Writes are *append-only* (no deletes/overwrites in this module).
- Data is written using :meth:`pandas.DataFrame.to_sql` with
  ``if_exists="append"``.
"""

import pandas as pd
from sqlalchemy import create_engine

from peer_elt.config import StorageConfig
from peer_elt.interfaces import Storage


def _engine(config: StorageConfig):
    """Create a SQLAlchemy engine for PostgreSQL.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration. Requires ``config.postgres_url`` to be set.

    Returns
    -------
    sqlalchemy.engine.Engine
        SQLAlchemy engine configured for the given PostgreSQL URL.

    Raises
    ------
    ValueError
        If ``config.postgres_url`` is not set.
    """
    if not config.postgres_url:
        raise ValueError("postgres_url is required for postgres backend")
    return create_engine(config.postgres_url, future=True)


def load_raw_postgres(config: StorageConfig, df: pd.DataFrame) -> None:
    """Append raw preprint metadata to PostgreSQL.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration (PostgreSQL backend).
    df : pandas.DataFrame
        Raw metadata to append. If empty, no-op.

    Returns
    -------
    None

    Notes
    -----
    Data is appended to a table named ``raw_preprints``.
    """
    if df.empty:
        return
    engine = _engine(config)
    with engine.begin() as conn:
        df.to_sql("raw_preprints", conn, if_exists="append", index=False)


def write_table_postgres(config: StorageConfig, table_name: str, df: pd.DataFrame) -> None:
    """Append a named output table to PostgreSQL.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration (PostgreSQL backend).
    table_name : str
        Destination table name.
    df : pandas.DataFrame
        Output dataframe to append. If empty, no-op.

    Returns
    -------
    None

    Notes
    -----
    ``table_name`` is passed to :meth:`pandas.DataFrame.to_sql`. It is expected
    to be a trusted internal value (e.g., constants like ``"diff_features"``),
    not arbitrary user input.
    """
    if df.empty:
        return
    engine = _engine(config)
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)


def read_raw_postgres(config: StorageConfig) -> pd.DataFrame:
    """Read raw preprint metadata from PostgreSQL.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration (PostgreSQL backend).

    Returns
    -------
    pandas.DataFrame
        DataFrame containing all rows from ``raw_preprints``.
    """
    engine = _engine(config)
    return pd.read_sql("select * from raw_preprints", engine)


class PostgresStorage(Storage):
    """PostgreSQL-backed implementation of :class:`peer_elt.interfaces.Storage`.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration. Must include ``postgres_url``.
    """

    def __init__(self, config: StorageConfig) -> None:
        """Create a PostgreSQL storage backend.

        Parameters
        ----------
        config : peer_elt.config.StorageConfig
            Storage configuration used for all connections.

        Returns
        -------
        None
        """
        self._config = config

    def load_raw(self, df: pd.DataFrame) -> None:
        """Persist raw metadata by appending to ``raw_preprints``.

        Parameters
        ----------
        df : pandas.DataFrame
            Raw metadata to append.

        Returns
        -------
        None
        """
        load_raw_postgres(self._config, df)

    def read_raw(self) -> pd.DataFrame:
        """Read raw metadata from ``raw_preprints``.

        Returns
        -------
        pandas.DataFrame
            Raw metadata dataframe.
        """
        return read_raw_postgres(self._config)

    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        """Persist a named output dataset by appending to a PostgreSQL table.

        Parameters
        ----------
        table_name : str
            Destination table name.
        df : pandas.DataFrame
            Output dataframe to append.

        Returns
        -------
        None
        """
        write_table_postgres(self._config, table_name, df)
