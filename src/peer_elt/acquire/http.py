from __future__ import annotations

"""Retrying HTTP GET helper for full-text acquisition.

This module provides :class:`RequestsHttpGet`, a small callable wrapper around an
injected HTTP session (typically ``requests.Session``) that applies a consistent
retry policy using :mod:`tenacity`.

It exists to keep acquisition code (e.g., ``peer_elt.acquire.full_text``) clean,
testable, and free of direct network/retry concerns.

Key ideas
---------
- **Dependency injection**: callers pass in a ``session`` object that implements
  ``get(url, timeout, headers=...)``. This makes unit testing easy: tests can
  supply a fake session without network I/O.
- **Retry/backoff**: retry parameters come from :class:`peer_elt.config.RetryConfig`
  so the project has a single source of truth for retry behavior.

Retry policy
------------
Retries happen when either:
- ``session.get(...)`` raises an exception (e.g., transient network issues), OR
- the response status code is one of:

  - 429 (rate limited)
  - 500/502/503/504 (server or gateway errors)

Responses with non-retryable status codes (e.g., 404) are returned immediately.

Returned value
--------------
The callable returns a normalized :class:`ResponseLike` object containing only the
fields the rest of the pipeline needs:

- ``status_code`` (int)
- ``content`` (bytes)
- ``headers`` (mapping)

Notes
-----
- This module intentionally does not log retries; keeping it quiet makes tests
  deterministic and avoids noisy pipeline runs. If you want retry logs, add them
  at the orchestration layer (pipeline/CLI), where you already manage run logs.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol

from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

from peer_elt.config import RetryConfig


class _SessionLike(Protocol):
    """Minimal protocol for an HTTP session/client.

    Compatible with :class:`requests.Session` and simple fake sessions in tests.
    """

    def get(self, url: str, timeout: float, headers: Mapping[str, str] | None = None): ...


@dataclass(frozen=True)
class ResponseLike:
    """Normalized HTTP response shape used by acquisition code."""

    status_code: int
    content: bytes
    headers: Mapping[str, str]


# Status codes that are commonly transient and safe to retry.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _should_retry_response(resp: ResponseLike) -> bool:
    """Return True when the response indicates a transient failure."""
    return resp.status_code in _RETRYABLE_STATUSES


def _before_sleep(_retry_state: RetryCallState) -> None:
    """Tenacity callback executed before waiting between retries.

    Intentionally a no-op to keep this module quiet and deterministic.
    """
    return


class RequestsHttpGet:
    """HTTP GET callable with retry/backoff based on :class:`RetryConfig`.

    Parameters
    ----------
    session:
        Session-like HTTP client (e.g., ``requests.Session()``).
    retry:
        Retry/backoff configuration.

    Behavior
    --------
    - Retries on exceptions raised by the underlying ``session.get``.
    - Retries on responses with status codes in ``_RETRYABLE_STATUSES``.
    - Returns a :class:`ResponseLike` with status/content/headers copied from the
      underlying response object.
    """

    def __init__(self, session: _SessionLike, retry: RetryConfig) -> None:
        self._session = session
        self._retry = retry

        self._retrying = Retrying(
            stop=stop_after_attempt(retry.max_attempts),
            wait=wait_exponential(
                multiplier=retry.wait_multiplier,
                min=retry.wait_min_seconds,
                max=retry.wait_max_seconds,
            ),
            retry=(
                    retry_if_exception_type(Exception)  # conservative; narrow later if desired
                    | retry_if_result(_should_retry_response)
            ),
            reraise=True,
            before_sleep=_before_sleep,
        )

    def __call__(self, url: str, timeout_seconds: float) -> ResponseLike:
        """GET ``url`` with retries and return a normalized response."""
        def _do_get() -> ResponseLike:
            resp = self._session.get(
                url,
                timeout=timeout_seconds,
                headers={"User-Agent": "peer-elt/0.1 (+full-text-acquisition)"},
            )
            # requests.Response has .status_code, .content, .headers; fakes in tests can too.
            return ResponseLike(
                status_code=int(getattr(resp, "status_code")),
                content=bytes(getattr(resp, "content")),
                headers=dict(getattr(resp, "headers", {}) or {}),
            )

        return self._retrying(_do_get)
