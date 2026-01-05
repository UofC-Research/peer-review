from __future__ import annotations

"""Protocol-like interfaces for extractors, storages, and transformers.

These abstract base classes document required behaviors for each
pipeline component and enable easy swapping via factories.
"""

from abc import ABC, abstractmethod

import pandas as pd


class Extractor(ABC):
    """Interface for pulling preprint metadata from a source.

    Implementations should return a dataframe with the raw metadata
    fields used by downstream transforms (title, abstract, version, etc.).
    """

    @abstractmethod
    def fetch(self, source, retry_config) -> pd.DataFrame:
        """Return a dataframe of raw preprint metadata for a SourceConfig.

        Args:
            source: Source configuration including server and date range.
            retry_config: Retry/backoff configuration for external calls.
        """
        raise NotImplementedError


class Storage(ABC):
    """Interface for reading/writing pipeline data to a backend.

    Storage implementations should append new data and avoid destructive
    operations unless explicitly requested by the caller.
    """

    @abstractmethod
    def load_raw(self, df: pd.DataFrame) -> None:
        """Persist raw preprint metadata.

        Args:
            df: Raw metadata dataframe.
        """
        raise NotImplementedError

    @abstractmethod
    def read_raw(self) -> pd.DataFrame:
        """Load raw preprint metadata from storage.

        Returns:
            DataFrame of raw metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        """Write a named output table to storage.

        Args:
            table_name: Logical name for the output table.
            df: Output dataframe to persist.
        """
        raise NotImplementedError


class Transformer(ABC):
    """Interface for turning raw metadata into analytical features.

    Implementations should not mutate the input dataframe in-place.
    """

    @abstractmethod
    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Return an analysis-ready dataframe.

        Args:
            raw_df: Raw metadata dataframe.

        Returns:
            DataFrame of computed features.
        """
        raise NotImplementedError
