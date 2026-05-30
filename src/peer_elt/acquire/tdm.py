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
from pathlib import Path
from typing import Any, Mapping, Protocol

_SUPPORTED_TDM_SERVERS = {"biorxiv", "medrxiv"}
_PUBLISHED_METADATA_BASE_URL = "https://api.biorxiv.org/pubs"


@dataclass(frozen=True)
class TdmServerConfig:
    """Configuration for one bioRxiv/medRxiv TDM S3 resource."""

    server: str
    bucket: str
    region: str = "us-east-1"
    requester_pays: bool = True
    documentation_url: str | None = None

    def __post_init__(self) -> None:
        normalized = self.server.lower()
        if normalized not in _SUPPORTED_TDM_SERVERS:
            raise ValueError(f"Unsupported TDM server: {self.server}")
        object.__setattr__(self, "server", normalized)


@dataclass(frozen=True)
class TdmRepositoryConfig:
    """Configuration for optional bulk preprint full-text acquisition."""

    enabled: bool
    local_cache_dir: Path
    servers: list[TdmServerConfig]
    preferred_content_formats: tuple[str, ...] = ("xml", "pdf")
    expected_package_format: str = "meca_zip"

    def server(self, name: str) -> TdmServerConfig:
        """Return the configured TDM server by name."""
        normalized = name.lower()
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
        """Download or sync an S3 bucket/prefix into a local destination."""


class _ResponseLike(Protocol):
    status_code: int
    content: bytes
    headers: Mapping[str, str]


def tdm_config_from_mapping(payload: Mapping[str, Any]) -> TdmRepositoryConfig:
    """Build a TDM repository config from a YAML-style mapping."""
    if not isinstance(payload, Mapping):
        raise TypeError("`tdm_repository` must be a mapping")

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
                region=str(item.get("region", "us-east-1")),
                requester_pays=bool(item.get("requester_pays", True)),
                documentation_url=_optional_text(item.get("documentation_url")),
            )
        )

    preferred_formats = payload.get("preferred_content_formats", ("xml", "pdf"))
    if not isinstance(preferred_formats, (list, tuple)):
        raise TypeError("`tdm_repository.preferred_content_formats` must be a list")

    return TdmRepositoryConfig(
        enabled=bool(payload.get("enabled", False)),
        local_cache_dir=Path(str(payload.get("local_cache_dir", "data/raw/tdm"))),
        servers=servers,
        preferred_content_formats=tuple(str(fmt) for fmt in preferred_formats),
        expected_package_format=str(payload.get("expected_package_format", "meca_zip")),
    )


def download_tdm_preprint_archive(
        config: TdmRepositoryConfig,
        server: str,
        client: TdmArchiveClient,
) -> Path:
    """Download/sync one configured bioRxiv or medRxiv TDM preprint archive."""
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
    """Build the bioRxiv API URL for preprint-to-published metadata."""
    normalized = server.lower()
    if normalized not in _SUPPORTED_TDM_SERVERS:
        raise ValueError(f"Unsupported published metadata server: {server}")
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
    """Download bioRxiv API published-link metadata for one server/date window."""
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


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
