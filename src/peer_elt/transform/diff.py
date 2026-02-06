from __future__ import annotations

"""Diff and similarity feature construction for preprint versions.

This module computes within-DOI change features between the first observed
version (v1) and the latest observed version of a preprint.

Computed features include:
- Title and abstract string similarity ratios.
- Abstract word-count change (latest - v1).
- Optional PDF text similarity ratio (when enabled and PDFs are available).

Notes
-----
- Similarity ratios are computed using :class:`difflib.SequenceMatcher`.
- PDF text extraction uses :mod:`PyPDF2` if installed; missing dependencies or
  extraction failures result in empty text for that side of the comparison.
"""

from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import pandas as pd
from peer_elt.interfaces import Transformer


def _ratio(left: str, right: str) -> float:
    """Compute a similarity ratio between two strings.

    Parameters
    ----------
    left : str
        Left-hand string.
    right : str
        Right-hand string.

    Returns
    -------
    float
        Similarity ratio in the interval [0, 1]. Returns 1.0 when both strings
        are empty.
    """
    if not left and not right:
        return 1.0
    return SequenceMatcher(None, left or "", right or "").ratio()


def _word_count(text: str) -> int:
    """Count whitespace-delimited words.

    Parameters
    ----------
    text : str
        Input text.

    Returns
    -------
    int
        Number of whitespace-delimited tokens. Returns 0 for empty text.
    """
    if not text:
        return 0
    return len(text.split())


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file.

    Parameters
    ----------
    path : pathlib.Path
        Path to the PDF.

    Returns
    -------
    str
        Extracted text. Returns an empty string if the file does not exist, if
        :mod:`PyPDF2` is not installed, or if extraction fails.
    """
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

    Parameters
    ----------
    raw_df : pandas.DataFrame
        Raw metadata rows. Expected to contain at least ``doi`` and ``version``,
        and typically ``title`` and ``abstract``. If empty, an empty DataFrame is
        returned.
    enable_pdf_diff : bool
        If True, compute PDF text similarity for each DOI.
    pdf_dir : str | None
        Root directory containing PDF files. Expected layout is::

            <pdf_dir>/preprint/<doi>.pdf
            <pdf_dir>/published/<doi>.pdf

        Only used when ``enable_pdf_diff`` is True.

    Returns
    -------
    pandas.DataFrame
        Per-DOI feature table comparing v1 vs latest.

    Notes
    -----
    The implementation:
    - coerces ``version`` to numeric and uses per-DOI first/last ordering,
    - fills missing title/abstract with empty strings,
    - adds ``published_doi`` if missing (aliasing from API ``published`` field),
    - returns a normalized set of columns with stable names.
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
    merged["abstract_word_count_delta"] = merged["word_count_latest"] - merged["word_count_v1"]

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
    """Transformer that computes text and optional PDF similarity features.

    Parameters
    ----------
    enable_pdf_diff : bool
        Whether to compute PDF similarity features.
    pdf_dir : str | None
        Root directory containing PDFs, used only when ``enable_pdf_diff`` is
        True.
    """

    def __init__(self, enable_pdf_diff: bool, pdf_dir: Optional[str]) -> None:
        """Create the transformer.

        Parameters
        ----------
        enable_pdf_diff : bool
            Whether to compute PDF similarity features.
        pdf_dir : str | None
            Root directory containing PDFs.
        """
        self._enable_pdf_diff = enable_pdf_diff
        self._pdf_dir = pdf_dir

    def transform(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw metadata into per-DOI diff features.

        Parameters
        ----------
        raw_df : pandas.DataFrame
            Raw metadata dataframe.

        Returns
        -------
        pandas.DataFrame
            Diff feature table produced by :func:`build_diff_features`.
        """
        return build_diff_features(
            raw_df,
            enable_pdf_diff=self._enable_pdf_diff,
            pdf_dir=self._pdf_dir,
        )
