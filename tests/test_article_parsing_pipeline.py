from __future__ import annotations

"""Tests for the article parsing pipeline.

These tests verify `ArticleParsingPipeline` orchestration:
- fetching HTML,
- extracting main text, and
- passing section text to feature and embedding processors.
"""

from dataclasses import dataclass
from typing import Mapping

from peer_elt.parse.pipeline import ArticleDocument, ArticleParsingPipeline
from peer_elt.parse.processors import SimpleTokenStatsProcessor


@dataclass
class FakeScraper:
    """Fake scraper used to verify pipeline calls."""
    html: str
    text: str
    seen_url: str | None = None

    def fetch_article(self, url: str) -> str:
        """Return the configured HTML and record the URL."""
        self.seen_url = url
        return self.html

    def extract_text(self, html: str) -> str:
        """Return the configured extracted text.

        Args:
            html: HTML string to extract from.

        Returns:
            The configured article text.

        Raises:
            AssertionError: If the input HTML is not the expected value.
        """
        assert html == self.html
        return self.text


@dataclass
class FakeSpacy:
    """Fake feature processor capturing the sections it receives."""
    features: Mapping[str, Mapping[str, int]]
    seen: Mapping[str, str] | None = None

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        """Record sections and return predefined features."""
        self.seen = sections
        return self.features


@dataclass
class FakeSentenceBert:
    """Fake embedding processor capturing the sections it receives."""
    embeddings: Mapping[str, list[float]]
    seen: Mapping[str, str] | None = None

    def embed_sections(self, sections: Mapping[str, str]) -> Mapping[str, list[float]]:
        """Record sections and return predefined embeddings."""
        self.seen = sections
        return self.embeddings


def test_article_parsing_pipeline_scrapes_and_embeddings() -> None:
    """Pipeline should scrape, extract text, then compute features and embeddings."""
    scraper = FakeScraper(html="<html>mock</html>", text="Article body.")
    spacy = FakeSpacy(features={"article": {"token_count": 2, "sentence_count": 1}})
    sbert = FakeSentenceBert(embeddings={"article": [0.2, 0.3]})

    pipeline = ArticleParsingPipeline(
        scraper=scraper,
        spacy_processor=spacy,
        sentence_bert_processor=sbert,
    )
    parsed = pipeline.parse("https://example.org/article")

    assert scraper.seen_url == "https://example.org/article"
    assert spacy.seen == {"article": "Article body."}
    assert sbert.seen == {"article": "Article body."}
    assert parsed == ArticleDocument(
        source_url="https://example.org/article",
        html="<html>mock</html>",
        text="Article body.",
        features={"article": {"token_count": 2, "sentence_count": 1}},
        embeddings={"article": [0.2, 0.3]},
    )


def test_simple_token_stats_processor_handles_article_text() -> None:
    """SimpleTokenStatsProcessor should compute basic counts for article text."""
    processor = SimpleTokenStatsProcessor()

    result = processor.process_sections({"article": "Text only."})

    assert result["article"]["token_count"] == 2
    assert result["article"]["sentence_count"] == 1
