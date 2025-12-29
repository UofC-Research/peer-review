from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import pandas as pd


def _ratio(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    return SequenceMatcher(None, left or "", right or "").ratio()


def _word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def _extract_pdf_text(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return ""
    if not path.exists():
        return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def build_diff_features(
    raw_df: pd.DataFrame,
    enable_pdf_diff: bool,
    pdf_dir: Optional[str],
) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()

    frame = raw_df.copy()
    frame["abstract"] = frame.get("abstract", "").fillna("")
    frame["title"] = frame.get("title", "").fillna("")

    frame["word_count"] = frame["abstract"].map(_word_count)

    frame["version"] = pd.to_numeric(frame.get("version"), errors="coerce")
    frame["doi"] = frame.get("doi")

    base = frame.sort_values(["doi", "version"]).groupby("doi", as_index=False).first()
    latest = frame.sort_values(["doi", "version"]).groupby("doi", as_index=False).last()

    merged = base.merge(
        latest,
        on="doi",
        suffixes=("_v1", "_latest"),
        how="inner",
    )

    merged["title_diff_ratio"] = merged.apply(
        lambda row: _ratio(row["title_v1"], row["title_latest"]),
        axis=1,
    )
    merged["abstract_diff_ratio"] = merged.apply(
        lambda row: _ratio(row["abstract_v1"], row["abstract_latest"]),
        axis=1,
    )
    merged["abstract_word_count_delta"] = (
        merged["word_count_latest"] - merged["word_count_v1"]
    )

    if enable_pdf_diff and pdf_dir:
        pdf_root = Path(pdf_dir)
        merged["pdf_diff_ratio"] = merged.apply(
            lambda row: _ratio(
                _extract_pdf_text(pdf_root / "preprint" / f"{row['doi']}.pdf"),
                _extract_pdf_text(pdf_root / "published" / f"{row['doi']}.pdf"),
            ),
            axis=1,
        )
    else:
        merged["pdf_diff_ratio"] = None

    return merged[
        [
            "doi",
            "server_v1",
            "category_v1",
            "title_diff_ratio",
            "abstract_diff_ratio",
            "abstract_word_count_delta",
            "pdf_diff_ratio",
            "published_doi_v1",
            "published_doi_latest",
            "date_v1",
            "date_latest",
        ]
    ].rename(
        columns={
            "server_v1": "server",
            "category_v1": "category",
            "published_doi_v1": "published_doi_first",
            "published_doi_latest": "published_doi_latest",
            "date_v1": "date_first",
            "date_latest": "date_latest",
        }
    )
