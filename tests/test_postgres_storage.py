import pandas as pd
import pytest

from peer_elt.config import StorageConfig
from peer_elt.load import postgres


def test_engine_requires_url() -> None:
    with pytest.raises(ValueError, match="postgres_url is required"):
        postgres._engine(StorageConfig(backend="postgres"))


def test_load_raw_postgres_skips_empty(monkeypatch) -> None:
    def fail_engine(*_args, **_kwargs):
        raise AssertionError("engine should not be created for empty dataframes")

    monkeypatch.setattr(postgres, "create_engine", fail_engine)

    postgres.load_raw_postgres(StorageConfig(backend="postgres", postgres_url="x"), pd.DataFrame())


def test_write_table_postgres_skips_empty(monkeypatch) -> None:
    def fail_engine(*_args, **_kwargs):
        raise AssertionError("engine should not be created for empty dataframes")

    monkeypatch.setattr(postgres, "create_engine", fail_engine)

    postgres.write_table_postgres(
        StorageConfig(backend="postgres", postgres_url="x"),
        "diff_features",
        pd.DataFrame(),
    )
