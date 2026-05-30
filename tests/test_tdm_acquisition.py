from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from peer_elt.acquire.tdm import (
    TdmRepositoryConfig,
    TdmServerConfig,
    build_published_metadata_url,
    download_published_metadata,
    download_tdm_preprint_archive,
    tdm_config_from_mapping,
)


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    content: bytes
    headers: Mapping[str, str] | None = None


def test_tdm_config_accepts_biorxiv_and_medrxiv_servers(tmp_path: Path) -> None:
    payload = {
        "enabled": True,
        "local_cache_dir": str(tmp_path / "tdm"),
        "servers": [
            {
                "server": "biorxiv",
                "bucket": "s3://biorxiv-src-monthly",
                "region": "us-east-1",
                "requester_pays": True,
            },
            {
                "server": "medrxiv",
                "bucket": "s3://medrxiv-src-monthly",
                "region": "us-east-1",
                "requester_pays": True,
            },
        ],
    }

    config = tdm_config_from_mapping(payload)

    assert config.enabled is True
    assert config.local_cache_dir == tmp_path / "tdm"
    assert config.server("biorxiv").bucket == "s3://biorxiv-src-monthly"
    assert config.server("medrxiv").bucket == "s3://medrxiv-src-monthly"
    assert all(server.requester_pays for server in config.servers)


def test_tdm_config_from_mapping_rejects_unknown_server(tmp_path: Path) -> None:
    payload = {
        "enabled": True,
        "local_cache_dir": str(tmp_path / "tdm"),
        "servers": [{"server": "arxiv", "bucket": "s3://example"}],
    }

    with pytest.raises(ValueError, match="Unsupported TDM server"):
        tdm_config_from_mapping(payload)


def test_download_tdm_preprint_archive_uses_requester_pays_s3_settings(
        tmp_path: Path,
) -> None:
    calls: list[tuple[str, Path, str, bool]] = []

    class FakeTdmClient:
        def download_prefix(
                self,
                bucket: str,
                destination: Path,
                *,
                region: str,
                requester_pays: bool,
        ) -> None:
            calls.append((bucket, destination, region, requester_pays))

    config = TdmRepositoryConfig(
        enabled=True,
        local_cache_dir=tmp_path / "tdm",
        servers=[
            TdmServerConfig(
                server="biorxiv",
                bucket="s3://biorxiv-src-monthly",
                region="us-east-1",
                requester_pays=True,
            ),
            TdmServerConfig(
                server="medrxiv",
                bucket="s3://medrxiv-src-monthly",
                region="us-east-1",
                requester_pays=True,
            ),
        ],
    )

    biorxiv_destination = download_tdm_preprint_archive(
        config=config,
        server="biorxiv",
        client=FakeTdmClient(),
    )
    medrxiv_destination = download_tdm_preprint_archive(
        config=config,
        server="medrxiv",
        client=FakeTdmClient(),
    )

    assert biorxiv_destination == tmp_path / "tdm" / "biorxiv"
    assert medrxiv_destination == tmp_path / "tdm" / "medrxiv"
    assert calls == [
        ("s3://biorxiv-src-monthly", tmp_path / "tdm" / "biorxiv", "us-east-1", True),
        ("s3://medrxiv-src-monthly", tmp_path / "tdm" / "medrxiv", "us-east-1", True),
    ]


def test_build_published_metadata_url_supports_biorxiv_and_medrxiv() -> None:
    assert (
            build_published_metadata_url(
                server="biorxiv",
                date_from="2020-01-01",
                date_to="2020-01-31",
                cursor=100,
            )
            == "https://api.biorxiv.org/pubs/biorxiv/2020-01-01/2020-01-31/100"
    )
    assert (
            build_published_metadata_url(
                server="medrxiv",
                date_from="2020-02-01",
                date_to="2020-02-28",
            )
            == "https://api.biorxiv.org/pubs/medrxiv/2020-02-01/2020-02-28/0"
    )


def test_download_published_metadata_writes_api_payload(tmp_path: Path) -> None:
    calls: list[tuple[str, float]] = []

    def http_get(url: str, timeout_seconds: float) -> FakeResponse:
        calls.append((url, timeout_seconds))
        return FakeResponse(
            status_code=200,
            content=b'{"collection":[{"biorxiv_doi":"10.1101/example"}]}',
        )

    path = download_published_metadata(
        server="medrxiv",
        date_from="2020-03-01",
        date_to="2020-03-31",
        output_dir=tmp_path,
        http_get=http_get,
        timeout_seconds=12.0,
    )

    assert path == tmp_path / "medrxiv_published_metadata_2020-03-01_2020-03-31.json"
    assert path.read_text(encoding="utf-8") == (
        '{"collection":[{"biorxiv_doi":"10.1101/example"}]}'
    )
    assert calls == [
        ("https://api.biorxiv.org/pubs/medrxiv/2020-03-01/2020-03-31/0", 12.0)
    ]
