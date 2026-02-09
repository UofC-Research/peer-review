from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from peer_elt.acquire.http import RequestsHttpGet
from peer_elt.config import RetryConfig


@dataclass(frozen=True)
class FakeResp:
    status_code: int
    content: bytes = b"x"
    headers: Mapping[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", self.headers or {})


class FakeSession:
    def __init__(self, responses: list[FakeResp], raise_on_calls: set[int] | None = None) -> None:
        self._responses = responses
        self._raise_on_calls = raise_on_calls or set()
        self.calls: list[tuple[str, float]] = []
        self._call_index = 0

    def get(self, url: str, timeout: float, headers: Mapping[str, str] | None = None) -> FakeResp:
        self.calls.append((url, timeout))
        self._call_index += 1
        if self._call_index in self._raise_on_calls:
            raise RuntimeError("network down")
        return self._responses.pop(0)


def test_requests_http_get_retries_on_503_then_succeeds() -> None:
    session = FakeSession(
        responses=[
            FakeResp(status_code=503, content=b""),
            FakeResp(status_code=200, content=b"ok"),
        ]
    )
    retry = RetryConfig(max_attempts=3, wait_min_seconds=0, wait_max_seconds=0, wait_multiplier=0)

    http_get = RequestsHttpGet(session=session, retry=retry)
    resp = http_get("https://example.org/file.pdf", timeout_seconds=1.0)

    assert resp.status_code == 200
    assert resp.content == b"ok"
    assert len(session.calls) == 2


def test_requests_http_get_does_not_retry_on_404() -> None:
    session = FakeSession(responses=[FakeResp(status_code=404, content=b"nope")])
    retry = RetryConfig(max_attempts=5, wait_min_seconds=0, wait_max_seconds=0, wait_multiplier=0)

    http_get = RequestsHttpGet(session=session, retry=retry)
    resp = http_get("https://example.org/missing.pdf", timeout_seconds=1.0)

    assert resp.status_code == 404
    assert len(session.calls) == 1


def test_requests_http_get_retries_on_exception_then_succeeds() -> None:
    session = FakeSession(
        responses=[
            FakeResp(status_code=200, content=b"ok"),
        ],
        raise_on_calls={1},
    )
    retry = RetryConfig(max_attempts=3, wait_min_seconds=0, wait_max_seconds=0, wait_multiplier=0)

    http_get = RequestsHttpGet(session=session, retry=retry)
    resp = http_get("https://example.org/file.xml", timeout_seconds=1.0)

    assert resp.status_code == 200
    assert resp.content == b"ok"
    assert len(session.calls) == 2
