from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from peer_elt.parse.pipeline import ArticleDocument, ArticleParsingPipeline
from peer_elt.parse.processors import SimpleTokenStatsProcessor


@dataclass
class FakeScraper:
    html: str
    text: str
    seen_url: str | None = None

    def fetch_article(self, url: str) -> str:
        self.seen_url = url
        return self.html

    def extract_text(self, html: str) -> str:
        assert html == self.html
        return self.text


@dataclass
class FakeSpacy:
    features: Mapping[str, Mapping[str, int]]
    seen: Mapping[str, str] | None = None

    def process_sections(self, sections: Mapping[str, str]) -> Mapping[str, Mapping[str, int]]:
        self.seen = sections
        return self.features


@dataclass
class FakeSentenceBert:
    embeddings: Mapping[str, list[float]]
    seen: Mapping[str, str] | None = None

    def embed_sections(self, sections: Mapping[str, str]) -> Mapping[str, list[float]]:
        self.seen = sections
        return self.embeddings


def test_article_parsing_pipeline_scrapes_and_embeddings() -> None:
    scraper = FakeScraper(html="<html>mock</html>", text="Article body.")
    spacy = FakeSpacy(features={"article": {"token_count": 2, "sentence_count": 1}})
    sbert = FakeSentenceBert(embeddings={"article": [0.2, 0.3]})

    pipeline = ArticleParsingPipeline(scraper=scraper, spacy_processor=spacy, sentence_bert_processor=sbert)
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
    processor = SimpleTokenStatsProcessor()

    result = processor.process_sections({"article": "Text only."})

    assert result["article"]["token_count"] == 2
    assert result["article"]["sentence_count"] == 1
