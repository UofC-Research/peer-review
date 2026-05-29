from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

from peer_elt.config import RetryConfig, SourceConfig
from peer_elt.acquire.corpus import (
    MatchedManuscriptPair,
    acquire_matched_pair_full_text,
    query_preprint_servers_for_pairs,
    build_acquisition_requests,
    build_matched_manuscript_pairs,
)


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    content: bytes
    headers: Mapping[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", self.headers or {})


def test_build_pairs_selects_initial_preprint_version_and_published_doi() -> None:
    """The primary comparator is v1, while published DOI may appear later."""
    raw = pd.DataFrame(
        [
            {
                "doi": "10.1101/abc",
                "server": "biorxiv",
                "version": "2",
                "date": "2020-02-01",
                "published_doi": "10.7554/elife.abc",
            },
            {
                "doi": "10.1101/abc",
                "server": "biorxiv",
                "version": "1",
                "date": "2020-01-01",
                "published_doi": None,
            },
            {
                "doi": "10.1101/no-publication",
                "server": "biorxiv",
                "version": "1",
                "date": "2020-01-02",
                "published_doi": None,
            },
        ]
    )

    pairs = build_matched_manuscript_pairs(raw)

    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.manuscript_id == "biorxiv:10.1101/abc"
    assert pair.preprint_doi == "10.1101/abc"
    assert pair.preprint_version == "1"
    assert pair.preprint_date == "2020-01-01"
    assert pair.published_doi == "10.7554/elife.abc"


def test_query_preprint_servers_for_pairs_uses_configured_sources() -> None:
    """Query configured sources, then apply the matched-pair selection rules."""
    calls: list[tuple[str, str, str]] = []

    class FakeExtractor:
        def fetch(self, source: SourceConfig, retry_config: RetryConfig) -> pd.DataFrame:
            calls.append((source.server, source.date_from, source.date_to))
            return pd.DataFrame(
                [
                    {
                        "doi": "10.1101/abc",
                        "server": source.server,
                        "version": "1",
                        "date": source.date_from,
                        "published": "10.7554/elife.abc",
                    }
                ]
            )

    sources = [
        SourceConfig(
            name="biorxiv",
            server="biorxiv",
            date_from="2016-01-01",
            date_to="2022-12-31",
        )
    ]

    pairs = query_preprint_servers_for_pairs(
        sources=sources,
        extractor=FakeExtractor(),
        retry_config=RetryConfig(max_attempts=1),
    )

    assert calls == [("biorxiv", "2016-01-01", "2022-12-31")]
    assert len(pairs) == 1
    assert pairs[0].preprint_version == "1"
    assert pairs[0].published_doi == "10.7554/elife.abc"


def test_build_acquisition_requests_uses_preprint_v1_and_doi_resolver() -> None:
    """Build deterministic full-text URL candidates for both pair members."""
    pair = MatchedManuscriptPair(
        manuscript_id="biorxiv:10.1101/abc",
        server="biorxiv",
        preprint_doi="10.1101/abc",
        preprint_version="1",
        preprint_date="2020-01-01",
        published_doi="10.7554/elife.abc",
    )

    preprint, published = build_acquisition_requests(pair)

    assert preprint.doc_id == "biorxiv_10.1101_abc_v1_preprint"
    assert preprint.pdf_url == "https://www.biorxiv.org/content/10.1101/abcv1.full.pdf"
    assert preprint.html_url == "https://www.biorxiv.org/content/10.1101/abcv1"
    assert published.doc_id == "doi_10.7554_elife.abc_published"
    assert published.pdf_url is None
    assert published.xml_url is None
    assert published.html_url == "https://doi.org/10.7554/elife.abc"


def test_build_acquisition_requests_resolves_elife_full_text_candidates() -> None:
    """eLife DOIs should use publisher PDF/XML/HTML candidates before DOI fallback."""
    pair = MatchedManuscriptPair(
        manuscript_id="biorxiv:10.1101/elife",
        server="biorxiv",
        preprint_doi="10.1101/elife",
        preprint_version="1",
        preprint_date="2020-01-01",
        published_doi="10.7554/eLife.12345",
    )

    _, published = build_acquisition_requests(pair)

    assert published.doc_id == "doi_10.7554_eLife.12345_published"
    assert published.pdf_url == "https://elifesciences.org/articles/12345.pdf"
    assert published.xml_url == "https://elifesciences.org/articles/12345.xml"
    assert published.html_url == "https://elifesciences.org/articles/12345"


def test_build_acquisition_requests_resolves_plos_full_text_candidates() -> None:
    """PLOS DOIs should resolve to journal-specific PDF/XML/HTML candidates."""
    pair = MatchedManuscriptPair(
        manuscript_id="biorxiv:10.1101/plos",
        server="biorxiv",
        preprint_doi="10.1101/plos",
        preprint_version="1",
        preprint_date="2020-01-01",
        published_doi="10.1371/journal.pbio.3000001",
    )

    _, published = build_acquisition_requests(pair)

    article_url = "https://journals.plos.org/plosbiology/article"
    doi = "10.1371/journal.pbio.3000001"
    assert published.pdf_url == f"{article_url}/file?id={doi}&type=printable"
    assert published.xml_url == f"{article_url}/file?id={doi}&type=manuscript"
    assert published.html_url == f"{article_url}?id={doi}"


def test_acquire_matched_pair_full_text_downloads_preprint_and_published(
        tmp_path: Path,
) -> None:
    """Acquisition can download both sides through the existing downloader."""
    calls: list[str] = []

    def http_get(url: str, timeout: float) -> FakeResponse:
        calls.append(url)
        if url.endswith(".full.pdf"):
            return FakeResponse(200, b"%PDF preprint")
        if url == "https://www.biorxiv.org/content/10.1101/abcv1":
            return FakeResponse(200, b"<html>initial preprint</html>")
        if url.startswith("https://doi.org/"):
            return FakeResponse(200, b"<html>published article</html>")
        return FakeResponse(404, b"")

    pair = MatchedManuscriptPair(
        manuscript_id="biorxiv:10.1101/abc",
        server="biorxiv",
        preprint_doi="10.1101/abc",
        preprint_version="1",
        preprint_date="2020-01-01",
        published_doi="10.7554/elife.abc",
    )

    result = acquire_matched_pair_full_text(
        pair=pair,
        base_dir=tmp_path,
        http_get=http_get,
    )

    assert result.pair == pair
    assert result.preprint.success is True
    assert result.preprint.format == "html"
    assert result.published.success is True
    assert result.published.format == "html"
    assert result.preprint.path is not None
    assert result.published.path is not None
    assert result.preprint.path.read_bytes() == b"<html>initial preprint</html>"
    assert result.published.path.read_bytes() == b"<html>published article</html>"
    assert calls == [
        "https://doi.org/10.7554/elife.abc",
        "https://www.biorxiv.org/content/10.1101/abcv1",
    ]
