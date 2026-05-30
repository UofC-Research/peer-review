from __future__ import annotations

"""Text and Data Mining repository acquisition helpers.

bioRxiv and medRxiv expose requester-pays S3 repositories for bulk preprint
full-text access. This module keeps that acquisition path explicit and
dependency-injected: production code can provide an AWS/S3 implementation, while
tests can validate behavior with a small fake client.

The TDM repositories cover preprint full-text packages. Published-link metadata
for bioRxiv/medRxiv manuscripts is retrieved from the bioRxiv API `pubs`
endpoint; published-article full text remains an article-level publisher or DOI
resolver concern.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from peer_elt.acquire.corpus import MatchedManuscriptPair, build_acquisition_requests
from peer_elt.acquire.full_text import AcquisitionResult, acquire_full_text
from peer_elt.config import SourceConfig

_DEFAULT_CACHE_DIR = Path("data/raw/tdm")
_DEFAULT_PACKAGE_FORMAT = "meca_zip"
_DEFAULT_REGION = "us-east-1"
_DEFAULT_TDM_FORMATS = ("xml", "pdf", "html")
_PUBLISHED_METADATA_BASE_URL = "https://api.biorxiv.org/pubs"
_SUPPORTED_TDM_SERVERS = {"biorxiv", "medrxiv"}


@dataclass(frozen=True)
class TdmServerConfig:
    """Configuration for one bioRxiv/medRxiv TDM S3 resource.

    Parameters
    ----------
    server:
        Preprint server name. Supported values are ``"biorxiv"`` and
        ``"medrxiv"``.
    bucket:
        S3 bucket or prefix containing the TDM archive.
    region:
        AWS region for the bucket.
    requester_pays:
        Whether requests must be sent with requester-pays semantics.
    documentation_url:
        Optional public documentation URL for the server-specific TDM resource.

    Raises
    ------
    ValueError
        If ``server`` is not a supported bioRxiv/medRxiv TDM source.
    """

    server: str
    bucket: str
    region: str = "us-east-1"
    requester_pays: bool = True
    documentation_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "server", _normalize_supported_server(self.server))


@dataclass(frozen=True)
class TdmRepositoryConfig:
    """Configuration for optional bulk preprint full-text acquisition.

    Parameters
    ----------
    enabled:
        Whether local TDM archive acquisition is enabled.
    local_cache_dir:
        Directory where downloaded/synced TDM archives should be stored.
    servers:
        Server-specific TDM resource definitions.
    preferred_content_formats:
        Ordered content formats to prefer when unpacking, selecting, or
        pairing manuscript files. XML should be preferred for structured
        comparison, followed by PDF and then HTML.
    published_content_formats:
        Ordered content formats to attempt for matched published articles.
    expected_package_format:
        Expected archive/package format. Current bioRxiv/medRxiv TDM packages
        are documented as MECA zip packages.
    """

    enabled: bool
    local_cache_dir: Path
    servers: list[TdmServerConfig]
    preferred_content_formats: tuple[str, ...] = _DEFAULT_TDM_FORMATS
    published_content_formats: tuple[str, ...] = _DEFAULT_TDM_FORMATS
    expected_package_format: str = "meca_zip"

    def server(self, name: str) -> TdmServerConfig:
        """Return the configured TDM server by name.

        Parameters
        ----------
        name:
            Server name to look up.

        Returns
        -------
        TdmServerConfig
            Matching server configuration.

        Raises
        ------
        KeyError
            If ``name`` is supported but absent from this config.
        ValueError
            If ``name`` is not a supported TDM source.
        """
        normalized = _normalize_supported_server(name)
        for server_config in self.servers:
            if server_config.server == normalized:
                return server_config
        raise KeyError(f"TDM server is not configured: {name}")


class TdmArchiveClient(Protocol):
    """Client protocol for syncing/downloading a requester-pays S3 prefix."""

    def download_prefix(
            self,
            bucket: str,
            destination: Path,
            *,
            region: str,
            requester_pays: bool,
    ) -> None:
        """Download or sync an S3 bucket/prefix into a local destination.

        Parameters
        ----------
        bucket:
            S3 bucket or prefix to download.
        destination:
            Local directory that should receive the archive contents.
        region:
            AWS region for the bucket.
        requester_pays:
            Whether requester-pays mode should be used.
        """


@dataclass(frozen=True)
class AwsCliTdmArchiveClient:
    """AWS CLI implementation of the TDM archive client protocol.

    Parameters
    ----------
    aws_executable:
        AWS CLI executable name or path.
    runner:
        Callable used to execute the command. Defaults to ``subprocess.run`` and
        is injectable for tests.
    """

    aws_executable: str = "aws"
    runner: Callable[..., object] = subprocess.run

    def download_prefix(
            self,
            bucket: str,
            destination: Path,
            *,
            region: str,
            requester_pays: bool,
    ) -> None:
        """Sync an S3 bucket/prefix to a local destination with AWS CLI.

        Parameters
        ----------
        bucket:
            S3 bucket or prefix to sync.
        destination:
            Local destination directory.
        region:
            AWS region for the bucket.
        requester_pays:
            Whether to include ``--request-payer requester``.
        """
        command = [
            self.aws_executable,
            "s3",
            "sync",
            bucket,
            str(destination),
            "--region",
            region,
        ]
        if requester_pays:
            command.extend(["--request-payer", "requester"])
        self.runner(command, check=True)


@dataclass(frozen=True)
class TdmAutomatedAcquisitionResult:
    """Result of an automated TDM acquisition run.

    Parameters
    ----------
    preprint_archive_dirs:
        Local archive directories keyed by preprint server.
    published_metadata_paths:
        JSON metadata payloads downloaded from the bioRxiv ``pubs`` API.
    published_full_text_results:
        Full-text acquisition results for published articles linked from the
        metadata payloads.
    """

    preprint_archive_dirs: dict[str, Path]
    published_metadata_paths: list[Path]
    published_full_text_results: list[AcquisitionResult]


class _ResponseLike(Protocol):
    status_code: int
    content: bytes
    headers: Mapping[str, str]


def tdm_config_from_mapping(payload: Mapping[str, Any]) -> TdmRepositoryConfig:
    """Build a TDM repository config from a YAML-style mapping.

    Parameters
    ----------
    payload:
        Mapping loaded from a ``tdm_repository`` YAML block.

    Returns
    -------
    TdmRepositoryConfig
        Validated TDM repository configuration.

    Raises
    ------
    TypeError
        If the payload or nested sections have the wrong container type.
    KeyError
        If a server entry is missing required keys.
    ValueError
        If a server entry names an unsupported TDM source.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("`tdm_repository` must be a mapping")

    return TdmRepositoryConfig(
        enabled=bool(payload.get("enabled", False)),
        local_cache_dir=Path(str(payload.get("local_cache_dir", _DEFAULT_CACHE_DIR))),
        servers=_server_configs_from_mapping(payload),
        preferred_content_formats=_preferred_formats_from_mapping(payload),
        published_content_formats=_published_formats_from_mapping(payload),
        expected_package_format=str(
            payload.get("expected_package_format", _DEFAULT_PACKAGE_FORMAT)
        ),
    )


def download_tdm_preprint_archive(
        config: TdmRepositoryConfig,
        server: str,
        client: TdmArchiveClient,
) -> Path:
    """Download or sync one configured TDM preprint archive.

    Parameters
    ----------
    config:
        TDM repository configuration.
    server:
        Server name to sync. Supported values are ``"biorxiv"`` and
        ``"medrxiv"``.
    client:
        Client implementing the archive download/sync protocol.

    Returns
    -------
    pathlib.Path
        Local destination directory for the synced server archive.

    Raises
    ------
    ValueError
        If TDM acquisition is disabled, or if ``server`` is unsupported.
    KeyError
        If ``server`` is supported but not present in ``config``.
    """
    if not config.enabled:
        raise ValueError("TDM repository acquisition is disabled")

    server_config = config.server(server)
    destination = config.local_cache_dir / server_config.server
    destination.mkdir(parents=True, exist_ok=True)
    client.download_prefix(
        server_config.bucket,
        destination,
        region=server_config.region,
        requester_pays=server_config.requester_pays,
    )
    return destination


def build_published_metadata_url(
        server: str,
        date_from: str,
        date_to: str,
        cursor: int = 0,
) -> str:
    """Build the bioRxiv API URL for preprint-to-published metadata.

    Parameters
    ----------
    server:
        Preprint server name, either ``"biorxiv"`` or ``"medrxiv"``.
    date_from:
        Inclusive start date for the API interval.
    date_to:
        Inclusive end date for the API interval.
    cursor:
        API pagination cursor.

    Returns
    -------
    str
        Fully qualified ``pubs`` API URL.

    Raises
    ------
    ValueError
        If ``server`` is unsupported.
    """
    normalized = _normalize_supported_server(server, label="published metadata server")
    return f"{_PUBLISHED_METADATA_BASE_URL}/{normalized}/{date_from}/{date_to}/{cursor}"


def download_published_metadata(
        server: str,
        date_from: str,
        date_to: str,
        output_dir: Path,
        http_get,
        timeout_seconds: float = 30.0,
        cursor: int = 0,
) -> Path:
    """Download published-link metadata for one server/date window.

    Parameters
    ----------
    server:
        Preprint server name, either ``"biorxiv"`` or ``"medrxiv"``.
    date_from:
        Inclusive start date for the API interval.
    date_to:
        Inclusive end date for the API interval.
    output_dir:
        Directory where the JSON response body should be written.
    http_get:
        Injected HTTP getter accepting ``(url, timeout_seconds)``.
    timeout_seconds:
        Per-request timeout passed to ``http_get``.
    cursor:
        API pagination cursor.

    Returns
    -------
    pathlib.Path
        Path to the written JSON payload.

    Raises
    ------
    RuntimeError
        If the API response is not HTTP 200 or has an empty body.
    ValueError
        If ``server`` is unsupported.
    """
    url = build_published_metadata_url(
        server=server,
        date_from=date_from,
        date_to=date_to,
        cursor=cursor,
    )
    response: _ResponseLike = http_get(url, timeout_seconds)
    if response.status_code != 200 or not response.content:
        status = response.status_code
        raise RuntimeError(
            f"Published metadata request failed for {server}: HTTP {status}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{server.lower()}_published_metadata_{date_from}_{date_to}.json"
    path = output_dir / filename
    path.write_bytes(response.content)
    return path


def acquire_tdm_preprints_and_published_articles(
        config: TdmRepositoryConfig,
        sources: Iterable[SourceConfig],
        archive_client: TdmArchiveClient,
        metadata_http_get,
        article_http_get,
        timeout_seconds: float = 30.0,
        cursor: int = 0,
) -> TdmAutomatedAcquisitionResult:
    """Automate TDM preprint sync and linked published article retrieval.

    Parameters
    ----------
    config:
        Enabled TDM repository configuration.
    sources:
        Preprint source date windows used for published-link metadata requests.
    archive_client:
        Client used to sync requester-pays TDM preprint archives.
    metadata_http_get:
        HTTP getter for the bioRxiv ``pubs`` API.
    article_http_get:
        HTTP getter for published article full-text retrieval.
    timeout_seconds:
        Per-request timeout for metadata and published full-text requests.
    cursor:
        bioRxiv ``pubs`` API cursor.

    Returns
    -------
    TdmAutomatedAcquisitionResult
        Archive directories, metadata payload paths, and published article
        acquisition results.

    Raises
    ------
    ValueError
        If TDM acquisition is disabled or a source server is unsupported.
    """
    if not config.enabled:
        raise ValueError("TDM repository acquisition is disabled")

    source_list = list(sources)
    archive_dirs = _sync_tdm_archives(
        config=config,
        sources=source_list,
        archive_client=archive_client,
    )
    metadata_paths = _download_published_metadata_for_sources(
        sources=source_list,
        output_dir=config.local_cache_dir / "published_metadata",
        metadata_http_get=metadata_http_get,
        timeout_seconds=timeout_seconds,
        cursor=cursor,
    )
    published_results = _download_published_articles_from_metadata(
        metadata_paths=metadata_paths,
        output_dir=config.local_cache_dir / "published_full_text",
        article_http_get=article_http_get,
        timeout_seconds=timeout_seconds,
        attempt_order=config.published_content_formats,
    )
    return TdmAutomatedAcquisitionResult(
        preprint_archive_dirs=archive_dirs,
        published_metadata_paths=metadata_paths,
        published_full_text_results=published_results,
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _preferred_formats_from_mapping(payload: Mapping[str, Any]) -> tuple[str, ...]:
    preferred_formats = payload.get("preferred_content_formats", _DEFAULT_TDM_FORMATS)
    return _content_formats_from_value(
        preferred_formats,
        field_name="`tdm_repository.preferred_content_formats`",
    )


def _published_formats_from_mapping(payload: Mapping[str, Any]) -> tuple[str, ...]:
    published_block = payload.get("published_full_text", {})
    if published_block is None:
        published_block = {}
    if not isinstance(published_block, Mapping):
        raise TypeError("`tdm_repository.published_full_text` must be a mapping")
    formats = published_block.get(
        "preferred_content_formats",
        payload.get("preferred_content_formats", _DEFAULT_TDM_FORMATS),
    )
    return _content_formats_from_value(
        formats,
        field_name="`tdm_repository.published_full_text.preferred_content_formats`",
    )


def _content_formats_from_value(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be a list")
    formats = tuple(str(fmt) for fmt in value)
    unsupported = set(formats) - {"xml", "pdf", "html"}
    if unsupported:
        unsupported_formats = sorted(unsupported)
        raise ValueError(
            f"{field_name} includes unsupported formats: {unsupported_formats}"
        )
    return formats


def _server_configs_from_mapping(payload: Mapping[str, Any]) -> list[TdmServerConfig]:
    servers_payload = payload.get("servers", [])
    if not isinstance(servers_payload, list):
        raise TypeError("`tdm_repository.servers` must be a list")

    servers: list[TdmServerConfig] = []
    for idx, item in enumerate(servers_payload):
        if not isinstance(item, Mapping):
            raise TypeError(
                "`tdm_repository.servers` entries must be mappings; "
                f"item {idx} is {type(item).__name__}"
            )
        servers.append(
            TdmServerConfig(
                server=str(item["server"]),
                bucket=str(item["bucket"]),
                region=str(item.get("region", _DEFAULT_REGION)),
                requester_pays=bool(item.get("requester_pays", True)),
                documentation_url=_optional_text(item.get("documentation_url")),
            )
        )
    return servers


def _normalize_supported_server(value: str, label: str = "TDM server") -> str:
    normalized = value.lower()
    if normalized not in _SUPPORTED_TDM_SERVERS:
        raise ValueError(f"Unsupported {label}: {value}")
    return normalized


def _sync_tdm_archives(
        config: TdmRepositoryConfig,
        sources: Sequence[SourceConfig],
        archive_client: TdmArchiveClient,
) -> dict[str, Path]:
    archive_dirs: dict[str, Path] = {}
    for server in _unique_source_servers(sources):
        archive_dirs[server] = download_tdm_preprint_archive(
            config=config,
            server=server,
            client=archive_client,
        )
    return archive_dirs


def _download_published_metadata_for_sources(
        sources: Sequence[SourceConfig],
        output_dir: Path,
        metadata_http_get,
        timeout_seconds: float,
        cursor: int,
) -> list[Path]:
    return [
        download_published_metadata(
            server=source.server,
            date_from=source.date_from,
            date_to=source.date_to,
            output_dir=output_dir,
            http_get=metadata_http_get,
            timeout_seconds=timeout_seconds,
            cursor=cursor,
        )
        for source in sources
    ]


def _download_published_articles_from_metadata(
        metadata_paths: Sequence[Path],
        output_dir: Path,
        article_http_get,
        timeout_seconds: float,
        attempt_order: Sequence[str],
) -> list[AcquisitionResult]:
    results: list[AcquisitionResult] = []
    for metadata_path in metadata_paths:
        server = _server_from_metadata_filename(metadata_path)
        for request in _published_requests_from_metadata(metadata_path, server):
            results.append(
                acquire_full_text(
                    request=request,
                    base_dir=output_dir,
                    http_get=article_http_get,
                    timeout_seconds=timeout_seconds,
                    attempt_order=attempt_order,
                )
            )
    return results


def _published_requests_from_metadata(
        metadata_path: Path,
        server: str,
):
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    collection = payload.get("collection", [])
    if not isinstance(collection, list):
        raise TypeError(
            f"Published metadata collection must be a list: {metadata_path}"
        )

    for idx, item in enumerate(collection):
        if not isinstance(item, Mapping):
            continue
        published_doi = _first_text(
            item,
            "published_doi",
            "published",
            "published_article_doi",
            "journal_doi",
        )
        if not published_doi:
            continue
        preprint_doi = _first_text(item, "biorxiv_doi", "preprint_doi", "doi")
        version = _first_text(item, "version", "preprint_version") or "1"
        pair = MatchedManuscriptPair(
            manuscript_id=f"{server}:{preprint_doi or idx}",
            server=server,
            preprint_doi=preprint_doi or f"tdm-metadata-{idx}",
            preprint_version=version,
            preprint_date=_first_text(item, "preprint_date", "date"),
            published_doi=published_doi,
        )
        _, published_request = build_acquisition_requests(pair)
        yield published_request


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _optional_text(payload.get(key))
        if value:
            return value
    return None


def _server_from_metadata_filename(path: Path) -> str:
    server = path.name.split("_published_metadata_", 1)[0]
    return _normalize_supported_server(server)


def _unique_source_servers(sources: Sequence[SourceConfig]) -> list[str]:
    seen: set[str] = set()
    servers: list[str] = []
    for source in sources:
        server = _normalize_supported_server(source.server)
        if server not in seen:
            seen.add(server)
            servers.append(server)
    return servers
