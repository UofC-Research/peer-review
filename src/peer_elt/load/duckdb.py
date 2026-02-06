from __future__ import annotations

"""DuckDB-backed storage implementation.

This module provides a DuckDB implementation of the pipeline storage interface
(:class:`peer_elt.interfaces.Storage`) plus a small set of functional helpers
used by the class.

Tables
------
raw_preprints
    Raw extracted metadata appended via :func:`load_raw_duckdb`.

{name}
    Named output tables appended via :func:`write_table_duckdb`, where ``name``
    is the ``table_name`` argument (e.g., ``"diff_features"``).

Notes
-----
- Writes are *append-only* (no deletes/overwrites in this module).
- Incoming schemas are used to create tables on first write.
"""

import duckdb
import pandas as pd

from peer_elt.config import StorageConfig
from peer_elt.interfaces import Storage


def _connect(config: StorageConfig) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration. Requires ``config.duckdb_path`` to be set.

    Returns
    -------
    duckdb.DuckDBPyConnection
        Open DuckDB connection to the configured database.

    Raises
    ------
    ValueError
        If ``config.duckdb_path`` is not set.
    """
    if not config.duckdb_path:
        raise ValueError("duckdb_path is required for duckdb backend")
    return duckdb.connect(config.duckdb_path)


def load_raw_duckdb(config: StorageConfig, df: pd.DataFrame) -> None:
    """Append raw preprint metadata into DuckDB.

    If the destination table does not exist, it is created using the schema of
    the incoming dataframe.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration (DuckDB backend).
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
    with _connect(config) as conn:
        conn.register("raw_df", df)
        conn.execute(
            "create table if not exists raw_preprints as select * from raw_df limit 0"
        )
        conn.execute("insert into raw_preprints select * from raw_df")


def write_table_duckdb(config: StorageConfig, table_name: str, df: pd.DataFrame) -> None:
    """Append a named output table into DuckDB.

    If the destination table does not exist, it is created using the schema of
    the incoming dataframe.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration (DuckDB backend).
    table_name : str
        Destination table name.
    df : pandas.DataFrame
        Output dataframe to append. If empty, no-op.

    Returns
    -------
    None

    Notes
    -----
    ``table_name`` is interpolated into SQL. It is expected to be a trusted
    internal value (e.g., constants like ``"diff_features"``), not arbitrary
    user input.
    """
    if df.empty:
        return
    with _connect(config) as conn:
        conn.register("out_df", df)
        conn.execute(
            f"create table if not exists {table_name} as select * from out_df limit 0"
        )
        conn.execute(f"insert into {table_name} select * from out_df")


def read_raw_duckdb(config: StorageConfig) -> pd.DataFrame:
    """Read raw preprint metadata from DuckDB.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration (DuckDB backend).

    Returns
    -------
    pandas.DataFrame
        DataFrame containing all rows from ``raw_preprints``.
    """
    with _connect(config) as conn:
        return conn.execute("select * from raw_preprints").df()


class DuckDBStorage(Storage):
    """DuckDB-backed implementation of :class:`peer_elt.interfaces.Storage`.

    Parameters
    ----------
    config : peer_elt.config.StorageConfig
        Storage configuration. Must include ``duckdb_path``.
    """

    def __init__(self, config: StorageConfig) -> None:
        """Create a DuckDB storage backend.

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
        load_raw_duckdb(self._config, df)

    def read_raw(self) -> pd.DataFrame:
        """Read raw metadata from ``raw_preprints``.

        Returns
        -------
        pandas.DataFrame
            Raw metadata dataframe.
        """
        return read_raw_duckdb(self._config)

    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        """Persist a named output dataset by appending to a DuckDB table.

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
        write_table_duckdb(self._config, table_name, df)
