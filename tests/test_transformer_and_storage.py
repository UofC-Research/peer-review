from pathlib import Path

import pandas as pd
from peer_elt.config import StorageConfig
from peer_elt.load.duckdb import DuckDBStorage
from peer_elt.transform.diff import DiffTransformer


def test_diff_transformer_basic() -> None:
    raw_df = pd.DataFrame(
        [
            {"doi": "10.1/abc", "version": "1", "title": "A", "abstract": "foo bar", "server": "biorxiv",
             "category": "bio", "published": None, "date": "2023-01-01"},
            {"doi": "10.1/abc", "version": "2", "title": "A revised", "abstract": "foo bar baz", "server": "biorxiv",
             "category": "bio", "published": None, "date": "2023-02-01"},
        ]
    )
    transformer = DiffTransformer(enable_pdf_diff=False, pdf_dir=None)
    diff_df = transformer.transform(raw_df)

    assert diff_df.shape[0] == 1
    assert "title_diff_ratio" in diff_df.columns
    assert diff_df.iloc[0]["abstract_word_count_delta"] == 1


def test_duckdb_storage_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "peer.duckdb"
    storage = DuckDBStorage(StorageConfig(backend="duckdb", duckdb_path=str(db_path)))

    raw_df = pd.DataFrame(
        [
            {"doi": "10.1/abc", "version": "1", "title": "A", "abstract": "foo", "server": "biorxiv", "category": "bio",
             "published": None, "date": "2023-01-01"},
        ]
    )
    storage.load_raw(raw_df)
    out_df = storage.read_raw()

    assert out_df.shape[0] == 1
