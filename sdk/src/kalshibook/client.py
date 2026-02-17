"""KalshiBook client -- query L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations

import os
from typing import Any

from kalshibook._http import HttpTransport
from kalshibook.exceptions import AuthenticationError


class KalshiBook:
    """Client for the KalshiBook API.

    Provides sync and async access to historical orderbook data,
    trades, candles, events, and settlements for Kalshi prediction markets.

    Usage::

        # Sync (default -- scripts and notebooks)
        client = KalshiBook("kb-your-api-key")

        # From environment variable
        client = KalshiBook.from_env()

        # Async
        client = KalshiBook("kb-your-api-key", sync=False)

        # Context manager
        with KalshiBook("kb-your-api-key") as client:
            ...

    Parameters
    ----------
    api_key : str, optional
        KalshiBook API key (must start with 'kb-'). If not provided,
        reads from KALSHIBOOK_API_KEY environment variable.
    base_url : str, optional
        API base URL. Default: https://api.kalshibook.io
    sync : bool, optional
        If True (default), use synchronous HTTP transport.
        Set to False for async usage in event loop contexts.
    timeout : float, optional
        Request timeout in seconds. Default: 30.0
    max_retries : int, optional
        Maximum retry attempts for rate-limited requests. Default: 3
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.kalshibook.io",
        sync: bool = True,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        resolved_key = api_key or os.environ.get("KALSHIBOOK_API_KEY", "")

        if not resolved_key:
            raise AuthenticationError(
                message=(
                    "No API key provided. Pass api_key= or set "
                    "KALSHIBOOK_API_KEY environment variable."
                ),
                status_code=0,
                response_body={},
            )

        if not resolved_key.startswith("kb-"):
            raise AuthenticationError(
                message=(
                    f"Invalid API key format. Keys must start with "
                    f"'kb-', got '{resolved_key[:10]}...'"
                ),
                status_code=0,
                response_body={},
            )

        self._transport = HttpTransport(
            api_key=resolved_key,
            base_url=base_url,
            sync=sync,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._sync = sync

    @classmethod
    def from_env(cls, **kwargs: Any) -> KalshiBook:
        """Create client using KALSHIBOOK_API_KEY environment variable."""
        return cls(api_key=None, **kwargs)

    # -- Context manager support (sync and async) --

    def __enter__(self) -> KalshiBook:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> KalshiBook:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    # -- Cleanup --

    def close(self) -> None:
        """Close the underlying HTTP transport (sync)."""
        self._transport.close()

    async def aclose(self) -> None:
        """Close the underlying HTTP transport (async)."""
        await self._transport.aclose()
