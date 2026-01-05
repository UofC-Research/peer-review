from __future__ import annotations

"""Diff and similarity feature construction for preprint versions."""

from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import pandas as pd
from peer_elt.interfaces import Transformer


def _ratio(left: str, right: str) -> float:
    """Return a similarity ratio between two strings."""
    if not left and not right:
        return 1.0
    return SequenceMatcher(None, left or "", right or "").ratio()


def _word_count(text: str) -> int:
    """Count whitespace-delimited words."""
    if not text:
        return 0
    return len(text.split())


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file, returning empty string on failure."""
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
    """Build diff metrics between version 1 and latest for each DOI.

    This computes string similarity ratios for titles and abstracts,
    word count deltas, and (optionally) PDF text similarity.
    """
    if raw_df.empty:
        return pd.DataFrame()

    frame = raw_df.copy()
    frame["abstract"] = frame.get("abstract", "").fillna("")
    frame["title"] = frame.get("title", "").fillna("")
    if "published_doi" not in frame.columns:
        frame["published_doi"] = frame.get("published")
    else:
        frame["published_doi"] = frame["published_doi"].fillna(frame.get("published"))

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


class DiffTransformer(Transformer):
    """Transformer that computes text and PDF similarity features."""

    def __init__(self, enable_pdf_diff: bool, pdf_dir: Optional[str]) -> None:
        """Create a diff transformer with optional PDF comparison."""
        self._enable_pdf_diff = enable_pdf_diff
        self._pdf_dir = pdf_dir

    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        return build_diff_features(
            raw_df,
            enable_pdf_diff=self._enable_pdf_diff,
            pdf_dir=self._pdf_dir,
        )
