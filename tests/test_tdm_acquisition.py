from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from peer_elt.acquire.tdm import (
    AwsCliTdmArchiveClient,
    TdmRepositoryConfig,
    TdmServerConfig,
    acquire_tdm_preprints_and_published_articles,
    aws_cli_environment_from_dotenv,
    build_published_metadata_url,
    download_published_metadata,
    download_tdm_preprint_archive,
    tdm_config_from_mapping,
)
from peer_elt.config import SourceConfig


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
    assert config.preferred_content_formats == ("xml", "pdf", "html")
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


def test_aws_cli_tdm_archive_client_uses_requester_payer_flag(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], check: bool) -> None:
        calls.append(command)
        assert check is True

    client = AwsCliTdmArchiveClient(runner=runner)

    client.download_prefix(
        "s3://biorxiv-src-monthly",
        tmp_path / "biorxiv",
        region="us-east-1",
        requester_pays=True,
    )

    assert calls == [
        [
            "aws",
            "s3",
            "sync",
            "s3://biorxiv-src-monthly",
            str(tmp_path / "biorxiv"),
            "--region",
            "us-east-1",
            "--request-payer",
            "requester",
        ]
    ]


def test_aws_cli_environment_from_dotenv_recognizes_lowercase_aws_keys(
        tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "aws_access_key_id=example-key",
                "aws_secret_access_key='example-secret'",
                "aws_session_token=\"example-token\"",
                "aws_default_region=us-east-1",
            ]
        ),
        encoding="utf-8",
    )

    env = aws_cli_environment_from_dotenv(
        dotenv_path,
        base_env={"PATH": "example-path"},
    )

    assert env is not None
    assert env["PATH"] == "example-path"
    assert env["AWS_ACCESS_KEY_ID"] == "example-key"
    assert env["AWS_SECRET_ACCESS_KEY"] == "example-secret"
    assert env["AWS_SESSION_TOKEN"] == "example-token"
    assert env["AWS_DEFAULT_REGION"] == "us-east-1"


def test_aws_cli_tdm_archive_client_loads_dotenv_credentials_for_subprocess(
        tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AWS_ACCESS_KEY_ID=example-key",
                "AWS_SECRET_ACCESS_KEY=example-secret",
            ]
        ),
        encoding="utf-8",
    )
    calls: list[dict[str, object]] = []

    def runner(command: list[str], **kwargs: object) -> None:
        calls.append({"command": command, **kwargs})

    client = AwsCliTdmArchiveClient(
        runner=runner,
        env_file=dotenv_path,
        base_env={"PATH": "example-path"},
    )

    client.download_prefix(
        "s3://medrxiv-src-monthly",
        tmp_path / "medrxiv",
        region="us-east-1",
        requester_pays=True,
    )

    assert len(calls) == 1
    assert calls[0]["check"] is True
    env = calls[0]["env"]
    assert isinstance(env, dict)
    assert env["AWS_ACCESS_KEY_ID"] == "example-key"
    assert env["AWS_SECRET_ACCESS_KEY"] == "example-secret"
    assert env["PATH"] == "example-path"


def test_acquire_tdm_preprints_and_published_articles_automates_tdm_workflow(
        tmp_path: Path,
) -> None:
    archive_calls: list[tuple[str, Path, str, bool]] = []
    metadata_calls: list[str] = []
    article_calls: list[str] = []

    class FakeTdmClient:
        def download_prefix(
                self,
                bucket: str,
                destination: Path,
                *,
                region: str,
                requester_pays: bool,
        ) -> None:
            archive_calls.append((bucket, destination, region, requester_pays))

    def metadata_http_get(url: str, timeout_seconds: float) -> FakeResponse:
        metadata_calls.append(url)
        if "/biorxiv/" in url:
            return FakeResponse(
                200,
                (
                    b'{"collection":[{"biorxiv_doi":"10.1101/bio",'
                    b'"version":"1","published_doi":"10.7554/eLife.12345"}]}'
                ),
            )
        return FakeResponse(
            200,
            (
                b'{"collection":[{"biorxiv_doi":"10.1101/med",'
                b'"version":"1","published":"10.1371/journal.pbio.3000001"}]}'
            ),
        )

    def article_http_get(url: str, timeout_seconds: float) -> FakeResponse:
        article_calls.append(url)
        if url.endswith(".xml") or "type=manuscript" in url:
            return FakeResponse(200, b"<article>published</article>")
        return FakeResponse(404, b"")

    config = TdmRepositoryConfig(
        enabled=True,
        local_cache_dir=tmp_path / "tdm",
        servers=[
            TdmServerConfig("biorxiv", "s3://biorxiv-src-monthly"),
            TdmServerConfig("medrxiv", "s3://medrxiv-src-monthly"),
        ],
    )
    sources = [
        SourceConfig("bio", "biorxiv", "2020-01-01", "2020-01-31"),
        SourceConfig("med", "medrxiv", "2020-02-01", "2020-02-28"),
    ]

    result = acquire_tdm_preprints_and_published_articles(
        config=config,
        sources=sources,
        archive_client=FakeTdmClient(),
        metadata_http_get=metadata_http_get,
        article_http_get=article_http_get,
        timeout_seconds=10,
    )

    assert result.preprint_archive_dirs == {
        "biorxiv": tmp_path / "tdm" / "biorxiv",
        "medrxiv": tmp_path / "tdm" / "medrxiv",
    }
    assert result.published_metadata_paths == [
        tmp_path / "tdm" / "published_metadata" / (
            "biorxiv_published_metadata_2020-01-01_2020-01-31.json"
        ),
        tmp_path / "tdm" / "published_metadata" / (
            "medrxiv_published_metadata_2020-02-01_2020-02-28.json"
        ),
    ]
    formats = [item.format for item in result.published_full_text_results]
    assert formats == ["xml", "xml"]
    assert archive_calls == [
        ("s3://biorxiv-src-monthly", tmp_path / "tdm" / "biorxiv", "us-east-1", True),
        ("s3://medrxiv-src-monthly", tmp_path / "tdm" / "medrxiv", "us-east-1", True),
    ]
    assert metadata_calls == [
        "https://api.biorxiv.org/pubs/biorxiv/2020-01-01/2020-01-31/0",
        "https://api.biorxiv.org/pubs/medrxiv/2020-02-01/2020-02-28/0",
    ]
    assert article_calls == [
        "https://elifesciences.org/articles/12345.xml",
        (
            "https://journals.plos.org/plosbiology/article/file?"
            "id=10.1371/journal.pbio.3000001&type=manuscript"
        ),
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
