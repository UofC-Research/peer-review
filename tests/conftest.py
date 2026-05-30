from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live-config",
        action="store",
        default=None,
        help=(
            "Path to a YAML config enabling opt-in live integration tests. "
            "Can also be set with PEER_REVIEW_LIVE_CONFIG."
        ),
    )


@pytest.fixture(scope="session")
def live_config(request: pytest.FixtureRequest) -> dict[str, Any]:
    config_value = request.config.getoption("--live-config") or os.environ.get(
        "PEER_REVIEW_LIVE_CONFIG"
    )
    if not config_value:
        pytest.skip("live integration tests require --live-config or PEER_REVIEW_LIVE_CONFIG")

    config_path = Path(config_value).expanduser()
    if not config_path.exists():
        pytest.skip(f"live integration config does not exist: {config_path}")

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        pytest.skip(f"live integration config must be a YAML mapping: {config_path}")
    if payload.get("enabled") is not True:
        pytest.skip(f"live integration config is not enabled: {config_path}")

    return payload
