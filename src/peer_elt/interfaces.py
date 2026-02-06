from __future__ import annotations

"""Abstract interfaces for pipeline components.

This module defines the minimal contracts that pipeline components must satisfy:

- :class:`Extractor` pulls raw metadata for a configured source.
- :class:`Storage` persists and retrieves raw and derived datasets.
- :class:`Transformer` converts raw metadata into analysis-ready features.

The project uses these interfaces to enable factory-based swapping of concrete
implementations (e.g., DuckDB vs PostgreSQL storage) while keeping the pipeline
logic stable.

Notes
-----
These are expressed as :class:`abc.ABC` abstract base classes rather than
``typing.Protocol`` to provide explicit runtime enforcement (i.e., subclasses
must implement the abstract methods).
"""

from abc import ABC, abstractmethod

import pandas as pd


class Extractor(ABC):
    """Abstract interface for pulling preprint metadata from a source.

    Implementations typically make network calls to an external API and must
    return a :class:`pandas.DataFrame` containing the raw fields required by
    downstream transformations (e.g., title, abstract, version, server, date).

    Notes
    -----
    This interface intentionally does not prescribe a full schema. In practice,
    the transform layer will define which columns are required.
    """

    @abstractmethod
    def fetch(self, source, retry_config) -> pd.DataFrame:
        """Fetch raw preprint metadata for a single configured source.

        Parameters
        ----------
        source
            Source configuration (typically a ``SourceConfig``) describing which
            server to query and what date range to extract.
        retry_config
            Retry/backoff configuration (typically a ``RetryConfig``) used to
            govern transient-error handling for external calls.

        Returns
        -------
        pandas.DataFrame
            Raw metadata rows for the requested source.

        Raises
        ------
        NotImplementedError
            Always raised by the abstract base class. Concrete implementations
            should raise exceptions appropriate to their transport layer
            (e.g., network errors) and/or configuration validation.
        """
        raise NotImplementedError


class Storage(ABC):
    """Abstract interface for reading and writing pipeline data.

    Storage implementations back the pipeline's persistence layer. They should
    support writing raw extracted data and writing derived outputs, and they
    should avoid destructive operations unless the caller explicitly requests
    them.

    Notes
    -----
    The interface models logical operations (load/read/write) rather than
    database-specific concepts. Concrete implementations may choose how they map
    these operations to tables, schemas, files, or partitions.
    """

    @abstractmethod
    def load_raw(self, df: pd.DataFrame) -> None:
        """Persist raw extracted metadata.

        Parameters
        ----------
        df : pandas.DataFrame
            Raw metadata rows to persist.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            Always raised by the abstract base class.
        """
        raise NotImplementedError

    @abstractmethod
    def read_raw(self) -> pd.DataFrame:
        """Read raw metadata from storage.

        Returns
        -------
        pandas.DataFrame
            DataFrame containing the stored raw metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        """Write a named output table/dataset.

        Parameters
        ----------
        table_name : str
            Logical name for the output dataset (e.g., ``"diff_features"``).
        df : pandas.DataFrame
            Output dataframe to persist.

        Returns
        -------
        None

        Raises
        ------
        NotImplementedError
            Always raised by the abstract base class.
        """
        raise NotImplementedError


class Transformer(ABC):
    """Abstract interface for converting raw data into analytical features.

    Implementations are responsible for producing derived, analysis-ready tables
    (e.g., within-manuscript diffs, scoring outputs).

    Notes
    -----
    Transformers should treat ``raw_df`` as immutable input and should not
    mutate it in-place.
    """

    @abstractmethod
    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw metadata into derived features.

        Parameters
        ----------
        raw_df : pandas.DataFrame
            Raw metadata dataframe.

        Returns
        -------
        pandas.DataFrame
            DataFrame containing derived features.
        """
        raise NotImplementedError
