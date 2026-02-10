from __future__ import annotations

"""Retrying HTTP GET helper for full-text acquisition.

This module exposes :class:`RequestsHttpGet`, a small callable wrapper around an
injected HTTP client (typically ``requests.Session``) that applies a consistent
retry + exponential backoff policy using :mod:`tenacity`.

Why this exists
---------------
Acquisition code needs to fetch remote full text (PDF/XML/HTML) reliably without
duplicating retry logic everywhere. This wrapper centralizes that behavior and
keeps callers simple and testable.

Design highlights
-----------------
- **Dependency injection**: callers pass a session-like object implementing
  ``get(url, timeout, headers=...)``. Tests can pass a fake session to avoid
  real network I/O.
- **Retry policy from config**: retry parameters are sourced from
  :class:`peer_elt.config.RetryConfig` to keep behavior consistent across the
  project.
- **Deterministic tests**: Tenacity's sleep is routed through a small wrapper
  so tests can monkeypatch the sleep function and assert backoff behavior
  without waiting in real time.

Retry behavior
--------------
A request is retried when either:
- the underlying ``session.get(...)`` raises an exception, OR
- the returned response has a retryable status code (see ``_RETRYABLE_STATUSES``).

Non-retryable status codes (e.g., 404) are returned immediately.

Return value
------------
The callable returns a normalized :class:`ResponseLike` with only the fields the
rest of the pipeline needs:

- ``status_code`` (int)
- ``content`` (bytes)
- ``headers`` (mapping)

Notes
-----
- This module intentionally does not log retries to keep unit tests quiet and
  pipeline runs less noisy. If retry logging is desired, prefer adding it at a
  higher orchestration layer (CLI/pipeline runner).
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import tenacity.nap
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

from peer_elt.config import RetryConfig


def _sleep(seconds: float) -> None:
    """Sleep hook used by Tenacity between retries.

    Why wrap ``tenacity.nap.sleep``?
    - Tenacity may capture the sleep callable when :class:`~tenacity.Retrying` is
      constructed.
    - Tests can monkeypatch ``tenacity.nap.sleep`` and this wrapper will still
      call the patched function at runtime.

    Parameters
    ----------
    seconds:
        Duration to sleep (in seconds).
    """
    tenacity.nap.sleep(seconds)


class _SessionLike(Protocol):
    """Minimal protocol for an HTTP session/client used by :class:`RequestsHttpGet`.

    This is intentionally small so that both ``requests.Session`` and simple
    in-test fakes can satisfy it.

    The return type is ``Any`` because callers may use real ``requests.Response``
    objects or fake response objects in tests; we only rely on the presence of
    ``status_code``, ``content``, and optionally ``headers``.
    """

    def get(
            self,
            url: str,
            timeout: float,
            headers: Mapping[str, str] | None = None,
    ) -> Any: ...


@dataclass(frozen=True)
class ResponseLike:
    """Normalized HTTP response shape used by acquisition code.

    Attributes
    ----------
    status_code:
        HTTP status code.
    content:
        Raw response body as bytes.
    headers:
        Response headers as a mapping.
    """

    status_code: int
    content: bytes
    headers: Mapping[str, str]


# Status codes that are commonly transient and safe to retry.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _should_retry_response(resp: ResponseLike) -> bool:
    """Return True when a response indicates a transient failure.

    Tenacity uses this predicate via ``retry_if_result`` to decide whether the
    *result* of a call should trigger another attempt.

    Parameters
    ----------
    resp:
        The normalized response returned by the wrapped GET call.
    """
    return resp.status_code in _RETRYABLE_STATUSES


def _before_sleep(_retry_state: RetryCallState) -> None:
    """Tenacity callback executed right before sleeping between retries.

    Kept as a no-op to avoid logging/side effects. If you want observability,
    consider adding logging in a higher-level orchestration layer.
    """
    return


class RequestsHttpGet:
    """Callable HTTP GET wrapper with retry/backoff behavior.

    Construct with a session-like client and a :class:`~peer_elt.config.RetryConfig`,
    then call the instance like a function:

    ``resp = http_get(url, timeout_seconds=1.0)``

    Parameters
    ----------
    session:
        Session-like HTTP client (e.g., ``requests.Session()``) implementing
        :meth:`_SessionLike.get`.
    retry:
        Retry/backoff configuration.

    Retries
    -------
    - Retries on exceptions raised by ``session.get`` (conservative default).
    - Retries on retryable HTTP status codes (429/5xx gateway/server failures).
    - Uses exponential backoff bounded by ``wait_min_seconds`` and ``wait_max_seconds``.

    Returns
    -------
    ResponseLike
        A normalized response object suitable for downstream pipeline code.
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
            sleep=_sleep,
        )

    def __call__(self, url: str, timeout_seconds: float) -> ResponseLike:
        """GET ``url`` with retries and return a normalized response.

        Parameters
        ----------
        url:
            URL to fetch.
        timeout_seconds:
            Per-attempt timeout forwarded to the underlying session.

        Notes
        -----
        - The timeout applies to each attempt, not the overall retry budget.
        - A static ``User-Agent`` is set to make requests easier to identify.
        """

        def _do_get() -> ResponseLike:
            resp = self._session.get(
                url,
                timeout=timeout_seconds,
                headers={"User-Agent": "peer-elt/0.1 (+full-text-acquisition)"},
            )
            # We normalize to avoid leaking the concrete response type (requests vs fake).
            return ResponseLike(
                status_code=int(getattr(resp, "status_code")),
                content=bytes(getattr(resp, "content")),
                headers=dict(getattr(resp, "headers", {}) or {}),
            )

        return self._retrying(_do_get)
