"""HTTP transport layer (httpx-based, sync and async)."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

import httpx

from kalshibook.exceptions import (
    AuthenticationError,
    CreditsExhaustedError,
    KalshiBookError,
    MarketNotFoundError,
    RateLimitError,
    ValidationError,
)

# Avoid circular import -- __init__.py imports client.py which imports _http.py.
# Phase 12 (PyPI publishing) can refactor to a single source of truth.
_VERSION = "0.1.0"

# Maps API error.code strings to SDK exception classes.
_ERROR_MAP: dict[str, type[KalshiBookError]] = {
    "invalid_api_key": AuthenticationError,
    "rate_limit_exceeded": RateLimitError,
    "credits_exhausted": CreditsExhaustedError,
    "market_not_found": MarketNotFoundError,
    "event_not_found": MarketNotFoundError,
    "settlement_not_found": MarketNotFoundError,
    "no_data_available": MarketNotFoundError,
    "validation_error": ValidationError,
    "invalid_timestamp": ValidationError,
}


def _retry_delay(attempt: int) -> float:
    """Exponential backoff with jitter: ~1s, ~2s, ~4s for attempts 0, 1, 2."""
    base = min(2**attempt, 8)
    jitter = random.uniform(0, 0.5)
    return base + jitter


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a typed SDK exception if the response indicates an error."""
    if response.is_success:
        return

    try:
        body: dict[str, Any] = response.json()
        error_info = body.get("error", {})
        code = error_info.get("code", "unknown_error")
        message = error_info.get("message", f"HTTP {response.status_code}")
    except Exception:
        body = {}
        code = "unknown_error"
        message = f"HTTP {response.status_code}"

    exc_cls = _ERROR_MAP.get(code, KalshiBookError)
    raise exc_cls(
        message=message,
        status_code=response.status_code,
        response_body=body,
    )


class HttpTransport:
    """Dual-mode HTTP transport with auth injection, retry, and error mapping.

    Wraps httpx.Client (sync) or httpx.AsyncClient (async) with:
    - Bearer token authentication header
    - Exponential backoff retry on rate_limit_exceeded (429)
    - No retry on credits_exhausted (429) -- raises immediately
    - Error code to SDK exception mapping
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        sync: bool = True,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._sync = sync
        self._max_retries = max_retries

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": f"kalshibook-python/{_VERSION}",
            "Accept": "application/json",
        }

        client_kwargs: dict[str, Any] = {
            "base_url": base_url,
            "headers": headers,
            "timeout": httpx.Timeout(timeout),
        }

        if sync:
            self._client: httpx.Client | httpx.AsyncClient = httpx.Client(
                **client_kwargs
            )
        else:
            self._client = httpx.AsyncClient(**client_kwargs)

    def request_sync(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send a synchronous HTTP request with retry on rate limits."""
        response: httpx.Response | None = None
        for attempt in range(self._max_retries):
            response = self._client.request(method, path, **kwargs)  # type: ignore[union-attr]
            if response.status_code == 429:
                # Check if credits_exhausted -- do NOT retry
                try:
                    err_body = response.json()
                    err_code = err_body.get("error", {}).get("code", "")
                except Exception:
                    err_code = ""

                if err_code == "credits_exhausted":
                    break

                # Rate limit -- retry with backoff
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = _retry_delay(attempt)
                else:
                    delay = _retry_delay(attempt)
                time.sleep(delay)
                continue
            else:
                break

        assert response is not None
        _raise_for_status(response)
        return response

    async def request_async(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Send an asynchronous HTTP request with retry on rate limits."""
        response: httpx.Response | None = None
        for attempt in range(self._max_retries):
            response = await self._client.request(method, path, **kwargs)  # type: ignore[union-attr]
            if response.status_code == 429:
                # Check if credits_exhausted -- do NOT retry
                try:
                    err_body = response.json()
                    err_code = err_body.get("error", {}).get("code", "")
                except Exception:
                    err_code = ""

                if err_code == "credits_exhausted":
                    break

                # Rate limit -- retry with backoff
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = _retry_delay(attempt)
                else:
                    delay = _retry_delay(attempt)
                await asyncio.sleep(delay)
                continue
            else:
                break

        assert response is not None
        _raise_for_status(response)
        return response

    def close(self) -> None:
        """Close the synchronous HTTP client."""
        self._client.close()  # type: ignore[union-attr]

    async def aclose(self) -> None:
        """Close the asynchronous HTTP client."""
        await self._client.aclose()  # type: ignore[union-attr]
