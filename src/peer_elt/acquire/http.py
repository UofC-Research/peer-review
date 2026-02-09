from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from tenacity import RetryCallState, Retrying, retry_if_exception_type, retry_if_result, stop_after_attempt, \
    wait_exponential

from peer_elt.config import RetryConfig


class _SessionLike(Protocol):
    def get(self, url: str, timeout: float, headers: Mapping[str, str] | None = None): ...


@dataclass(frozen=True)
class ResponseLike:
    status_code: int
    content: bytes
    headers: Mapping[str, str]


_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _should_retry_response(resp: ResponseLike) -> bool:
    return resp.status_code in _RETRYABLE_STATUSES


def _before_sleep(_retry_state: RetryCallState) -> None:
    # Intentionally no logging here to keep library quiet and deterministic in tests.
    # Upstream pipeline can log retries if desired.
    return


class RequestsHttpGet:
    """HTTP GET with retry/backoff based on RetryConfig.

    Retries on:
      - Exceptions raised by the underlying session.get(...)
      - HTTP status codes in {_RETRYABLE_STATUSES}
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
                    retry_if_exception_type(Exception)  # conservative; narrow later if you want
                    | retry_if_result(_should_retry_response)
            ),
            reraise=True,
            before_sleep=_before_sleep,
        )

    def __call__(self, url: str, timeout_seconds: float) -> ResponseLike:
        def _do_get() -> ResponseLike:
            resp = self._session.get(
                url,
                timeout=timeout_seconds,
                headers={"User-Agent": "peer-elt/0.1 (+full-text-acquisition)"},
            )
            # requests.Response has .status_code, .content, .headers; our FakeResp does too.
            return ResponseLike(
                status_code=int(getattr(resp, "status_code")),
                content=bytes(getattr(resp, "content")),
                headers=dict(getattr(resp, "headers", {}) or {}),
            )

        return self._retrying(_do_get)
