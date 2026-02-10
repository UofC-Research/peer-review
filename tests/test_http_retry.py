from __future__ import annotations

"""Tests for the retrying HTTP GET wrapper.

This module validates the behavior of `peer_elt.acquire.http.RequestsHttpGet`
without making real network requests.

What we test:
- Retry on transient server errors (e.g., HTTP 503).
- Do NOT retry on non-transient client errors (e.g., HTTP 404).
- Retry on exceptions raised by the underlying HTTP client.
- Apply a backoff delay (sleep) between retries to avoid flooding a provider.

How we test it:
- Use a small `FakeSession` with deterministic responses/exceptions.
- Monkeypatch Tenacity's internal sleep function so the test can assert that
  the wrapper is actually sleeping between attempts, without slowing the test.
"""

from dataclasses import dataclass
from typing import Mapping

import pytest
import tenacity.nap

from peer_elt.acquire.http import RequestsHttpGet
from peer_elt.config import RetryConfig


@dataclass(frozen=True)
class FakeResp:
    """Minimal fake HTTP response used by tests.

    Attributes:
        status_code: HTTP status code to simulate.
        content: Response payload bytes.
        headers: Response headers. Defaults to an empty mapping.
    """

    status_code: int
    content: bytes = b"x"
    headers: Mapping[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", self.headers or {})


class FakeSession:
    """Fake session with a `get` method compatible with `RequestsHttpGet`.

    Args:
        responses: Queue of responses to return on each call to `get`.
        raise_on_calls: Optional set of 1-based call indices on which `get`
            should raise `RuntimeError`.

    Attributes:
        calls: Captured `(url, timeout)` tuples for asserting call counts.
    """

    def __init__(self, responses: list[FakeResp], raise_on_calls: set[int] | None = None) -> None:
        self._responses = responses
        self._raise_on_calls = raise_on_calls or set()
        self.calls: list[tuple[str, float]] = []
        self._call_index = 0

    def get(self, url: str, timeout: float, headers: Mapping[str, str] | None = None) -> FakeResp:
        """Return the next response or raise an exception based on configuration."""
        self.calls.append((url, timeout))
        self._call_index += 1
        if self._call_index in self._raise_on_calls:
            raise RuntimeError("network down")
        return self._responses.pop(0)


def test_requests_http_get_retries_on_503_then_succeeds() -> None:
    """It retries on 503 and eventually returns the success response."""
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
    """It does not retry on 404 and returns immediately."""
    session = FakeSession(responses=[FakeResp(status_code=404, content=b"nope")])
    retry = RetryConfig(max_attempts=5, wait_min_seconds=0, wait_max_seconds=0, wait_multiplier=0)

    http_get = RequestsHttpGet(session=session, retry=retry)
    resp = http_get("https://example.org/missing.pdf", timeout_seconds=1.0)

    assert resp.status_code == 404
    assert len(session.calls) == 1


def test_requests_http_get_retries_on_exception_then_succeeds() -> None:
    """It retries when the session raises and then returns the success response."""
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


def test_requests_http_get_applies_backoff_delay_on_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """It sleeps between retry attempts to avoid flooding the provider.

    This test does not measure real time. Instead, it monkeypatches Tenacity's
    internal sleep function and asserts it is called with non-zero delays when
    the same URL is retried.
    """
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(float(seconds))

    monkeypatch.setattr(tenacity.nap, "sleep", fake_sleep)

    session = FakeSession(
        responses=[
            FakeResp(status_code=503, content=b""),
            FakeResp(status_code=503, content=b""),
            FakeResp(status_code=200, content=b"ok"),
        ]
    )
    retry = RetryConfig(
        max_attempts=5,
        wait_min_seconds=1,
        wait_max_seconds=60,
        wait_multiplier=1,
    )

    http_get = RequestsHttpGet(session=session, retry=retry)
    resp = http_get("https://example.org/same-query.pdf", timeout_seconds=1.0)

    assert resp.status_code == 200
    assert len(session.calls) == 3

    # Two retryable failures -> two sleeps before the final successful attempt.
    assert len(sleeps) == 2
    assert sleeps[0] >= 1.0
    assert sleeps[1] >= sleeps[0]
    assert sleeps[1] >= 2.0
