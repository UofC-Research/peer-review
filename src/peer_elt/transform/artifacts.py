from __future__ import annotations

"""Connect acquired full-text artifacts to methodology scoring.

This module provides a small design-pattern layer between acquisition, parsing,
and scoring:

- ``ArtifactParser`` is a Strategy interface for format-specific parsers.
- ``ArtifactParserRegistry`` selects a parser based on acquired format.
- ``AcquiredArtifactScoringWorkflow`` is a Facade that parses both acquired
  artifacts and delegates pair scoring to ``MethodologyScoringWorkflow``.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Mapping, Protocol

from peer_elt.acquire.corpus import PairAcquisitionResult
from peer_elt.acquire.full_text import AcquiredFormat, AcquisitionResult
from peer_elt.parse.interfaces import SentenceBertProcessor, SpacyProcessor
from peer_elt.parse.models import ArticleDocument
from peer_elt.parse.pipeline import PdfParsingPipeline
from peer_elt.parse.xml_reader import XmlSectionReader
from peer_elt.transform.methodology import MethodologyScoringWorkflow, PairScorecard


@dataclass(frozen=True)
class ParsedArtifact:
    """Parsed representation of one acquired full-text artifact.

    Attributes
    ----------
    format : peer_elt.acquire.full_text.AcquiredFormat
        Acquired full-text format used for parsing.
    path : pathlib.Path
        Local artifact path that was parsed.
    document
        Parsed document object or section mapping accepted by
        ``MethodologyScoringWorkflow``.
    """

    format: AcquiredFormat
    path: Path
    document: object


class ArtifactParser(Protocol):
    """Strategy interface for parsing an acquired artifact."""

    def parse(self, acquisition: AcquisitionResult) -> ParsedArtifact:
        """Parse one successful acquisition result.

        Parameters
        ----------
        acquisition : peer_elt.acquire.full_text.AcquisitionResult
            Successful acquisition result with format and local path.

        Returns
        -------
        ParsedArtifact
            Parsed artifact bundle.
        """


class HtmlTextExtractor(Protocol):
    """Strategy interface for extracting visible text from HTML."""

    def extract_text(self, html: str) -> str:
        """Extract text from an HTML string.

        Parameters
        ----------
        html : str
            Raw HTML content.

        Returns
        -------
        str
            Extracted article text.
        """


class PlainTextHtmlExtractor(HTMLParser):
    """Lightweight HTML-to-text extractor using the standard library parser."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def extract_text(self, html: str) -> str:
        """Extract visible text from HTML.

        Parameters
        ----------
        html : str
            Raw HTML content.

        Returns
        -------
        str
            Whitespace-normalized text content.
        """
        self._parts = []
        self._skip_depth = 0
        self.feed(html)
        self.close()
        return " ".join(" ".join(self._parts).split())

    def handle_starttag(self, tag: str, attrs) -> None:
        """Track script/style blocks that should not contribute text.

        Parameters
        ----------
        tag : str
            HTML start tag name.
        attrs
            Attributes supplied by ``html.parser.HTMLParser``.

        Returns
        -------
        None
        """
        if tag.lower() in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        """Stop skipping text after script/style blocks end.

        Parameters
        ----------
        tag : str
            HTML end tag name.

        Returns
        -------
        None
        """
        if tag.lower() in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        """Collect visible text nodes.

        Parameters
        ----------
        data : str
            Text node content supplied by ``html.parser.HTMLParser``.

        Returns
        -------
        None
        """
        if not self._skip_depth and data.strip():
            self._parts.append(data.strip())


class PdfArtifactParser:
    """Parse acquired PDF artifacts with an injected PDF parsing pipeline.

    Parameters
    ----------
    pipeline : peer_elt.parse.pipeline.PdfParsingPipeline
        Pipeline used to parse local PDF artifacts.
    """

    def __init__(self, pipeline: PdfParsingPipeline) -> None:
        self._pipeline = pipeline

    def parse(self, acquisition: AcquisitionResult) -> ParsedArtifact:
        """Parse an acquired PDF artifact.

        Parameters
        ----------
        acquisition : peer_elt.acquire.full_text.AcquisitionResult
            Successful PDF acquisition result.

        Returns
        -------
        ParsedArtifact
            Parsed PDF document bundle.
        """
        path = _require_successful_artifact(acquisition, "pdf")
        return ParsedArtifact(
            format="pdf",
            path=path,
            document=self._pipeline.parse(path),
        )


class HtmlArtifactParser:
    """Parse acquired HTML artifacts into ``ArticleDocument`` objects.

    Parameters
    ----------
    text_extractor : HtmlTextExtractor | None, default=None
        HTML text extraction strategy. Defaults to ``PlainTextHtmlExtractor``.
    spacy_processor : peer_elt.parse.interfaces.SpacyProcessor | None, default=None
        Optional feature processor applied to the extracted article text.
    sentence_bert_processor : peer_elt.parse.interfaces.SentenceBertProcessor | None, default=None
        Optional embedding processor applied to the extracted article text.
    encoding : str, default="utf-8"
        Text encoding used to read local HTML artifacts.
    """

    def __init__(
            self,
            text_extractor: HtmlTextExtractor | None = None,
            spacy_processor: SpacyProcessor | None = None,
            sentence_bert_processor: SentenceBertProcessor | None = None,
            encoding: str = "utf-8",
    ) -> None:
        self._text_extractor = text_extractor or PlainTextHtmlExtractor()
        self._spacy_processor = spacy_processor
        self._sentence_bert_processor = sentence_bert_processor
        self._encoding = encoding

    def parse(self, acquisition: AcquisitionResult) -> ParsedArtifact:
        """Parse an acquired HTML artifact.

        Parameters
        ----------
        acquisition : peer_elt.acquire.full_text.AcquisitionResult
            Successful HTML acquisition result.

        Returns
        -------
        ParsedArtifact
            Parsed article document bundle.
        """
        path = _require_successful_artifact(acquisition, "html")
        html = path.read_text(encoding=self._encoding, errors="replace")
        text = self._text_extractor.extract_text(html)
        sections = {"article": text}
        features = (
            self._spacy_processor.process_sections(sections)
            if self._spacy_processor
            else {}
        )
        embeddings = (
            self._sentence_bert_processor.embed_sections(sections)
            if self._sentence_bert_processor
            else {}
        )
        return ParsedArtifact(
            format="html",
            path=path,
            document=ArticleDocument(
                source_url=path.as_uri(),
                html=html,
                text=text,
                features=features,
                embeddings=embeddings,
            ),
        )


class XmlArtifactParser:
    """Parse acquired XML artifacts into section mappings.

    Parameters
    ----------
    reader : peer_elt.parse.xml_reader.XmlSectionReader
        XML reader strategy used to extract section text.
    encoding : str, default="utf-8"
        Text encoding used to read local XML artifacts.
    """

    def __init__(self, reader: XmlSectionReader, encoding: str = "utf-8") -> None:
        self._reader = reader
        self._encoding = encoding

    def parse(self, acquisition: AcquisitionResult) -> ParsedArtifact:
        """Parse an acquired XML artifact.

        Parameters
        ----------
        acquisition : peer_elt.acquire.full_text.AcquisitionResult
            Successful XML acquisition result.

        Returns
        -------
        ParsedArtifact
            Parsed XML section mapping.
        """
        path = _require_successful_artifact(acquisition, "xml")
        xml = path.read_text(encoding=self._encoding, errors="replace")
        return ParsedArtifact(
            format="xml",
            path=path,
            document=self._reader.read(xml),
        )


class ArtifactParserRegistry:
    """Registry/factory for selecting artifact parsers by acquired format.

    Parameters
    ----------
    parsers : Mapping[peer_elt.acquire.full_text.AcquiredFormat, ArtifactParser]
        Parser strategies keyed by acquired format.
    """

    def __init__(self, parsers: Mapping[AcquiredFormat, ArtifactParser]) -> None:
        self._parsers = dict(parsers)

    def parse(self, acquisition: AcquisitionResult) -> ParsedArtifact:
        """Parse an acquisition result with the parser matching its format.

        Parameters
        ----------
        acquisition : peer_elt.acquire.full_text.AcquisitionResult
            Successful acquisition result.

        Returns
        -------
        ParsedArtifact
            Parsed artifact bundle.

        Raises
        ------
        ValueError
            If the acquisition result is incomplete or its format is unsupported.
        """
        if acquisition.format is None:
            raise ValueError(f"Acquisition has no format: {acquisition.doc_id}")
        try:
            parser = self._parsers[acquisition.format]
        except KeyError as exc:
            raise ValueError(
                f"No artifact parser registered for format: {acquisition.format}"
            ) from exc
        return parser.parse(acquisition)


class AcquiredArtifactScoringWorkflow:
    """Facade connecting pair acquisition results to methodology scoring.

    Parameters
    ----------
    parser_registry : ArtifactParserRegistry
        Registry used to parse acquired preprint and published artifacts.
    scoring_workflow : peer_elt.transform.methodology.MethodologyScoringWorkflow
        Workflow used to score parsed artifact documents.
    """

    def __init__(
            self,
            parser_registry: ArtifactParserRegistry,
            scoring_workflow: MethodologyScoringWorkflow,
    ) -> None:
        self._parser_registry = parser_registry
        self._scoring_workflow = scoring_workflow

    def score(self, acquisition: PairAcquisitionResult) -> PairScorecard:
        """Parse and score one acquired matched manuscript pair.

        Parameters
        ----------
        acquisition : peer_elt.acquire.corpus.PairAcquisitionResult
            Acquisition result containing both preprint and published artifacts.

        Returns
        -------
        peer_elt.transform.methodology.PairScorecard
            Fixed methodology scorecard for the matched pair.
        """
        preprint = self._parser_registry.parse(acquisition.preprint)
        published = self._parser_registry.parse(acquisition.published)
        return self._scoring_workflow.score_pair(
            manuscript_id=acquisition.pair.manuscript_id,
            preprint_document=preprint.document,
            published_document=published.document,
            preprint_format=preprint.format,
            published_format=published.format,
        )


def _require_successful_artifact(
        acquisition: AcquisitionResult,
        expected_format: AcquiredFormat,
) -> Path:
    """Return a local artifact path after validating acquisition success.

    Parameters
    ----------
    acquisition : peer_elt.acquire.full_text.AcquisitionResult
        Acquisition result to validate.
    expected_format : peer_elt.acquire.full_text.AcquiredFormat
        Format expected by the parser strategy.

    Returns
    -------
    pathlib.Path
        Local path to the acquired artifact.

    Raises
    ------
    ValueError
        If the acquisition failed, has no local path, or has the wrong format.
    """
    if not acquisition.success:
        raise ValueError(f"Cannot parse failed acquisition: {acquisition.doc_id}")
    if acquisition.format != expected_format:
        raise ValueError(
            f"Expected {expected_format} artifact for {acquisition.doc_id}, "
            f"got {acquisition.format}"
        )
    if acquisition.path is None:
        raise ValueError(f"Acquisition has no local path: {acquisition.doc_id}")
    return acquisition.path


__all__ = [
    "AcquiredArtifactScoringWorkflow",
    "ArtifactParser",
    "ArtifactParserRegistry",
    "HtmlArtifactParser",
    "HtmlTextExtractor",
    "ParsedArtifact",
    "PdfArtifactParser",
    "PlainTextHtmlExtractor",
    "XmlArtifactParser",
]
