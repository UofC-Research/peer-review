from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Extractor(ABC):
    @abstractmethod
    def fetch(self, source) -> pd.DataFrame:
        raise NotImplementedError


class Storage(ABC):
    @abstractmethod
    def load_raw(self, df: pd.DataFrame) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_raw(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        raise NotImplementedError


class Transformer(ABC):
    @abstractmethod
    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
