"""Kalshi REST API client for market/event/series enrichment."""

from __future__ import annotations

import base64
import time

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from src.collector.metrics import get_logger

logger = get_logger("enrichment")


class KalshiRestClient:
    """Async client for Kalshi REST API enrichment calls.

    All methods return None on failure -- enrichment errors
    should never crash the collector.
    """

    def __init__(self, api_key_id: str, private_key, base_url: str):
        self._api_key_id = api_key_id
        self._private_key = private_key
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)

    def _generate_rest_headers(self, method: str, path: str) -> dict[str, str]:
        """Generate RSA-PSS authentication headers for Kalshi REST API.

        Signs: timestamp_ms + METHOD + path (same key/algo as WS auth).
        """
        timestamp_ms = str(int(time.time() * 1000))
        message = timestamp_ms + method.upper() + path
        signature = self._private_key.sign(
            message.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self._api_key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        }

    async def get_market(self, ticker: str) -> dict | None:
        """Fetch market data by ticker. Returns None on failure."""
        path = f"/markets/{ticker}"
        try:
            headers = self._generate_rest_headers("GET", f"/trade-api/v2{path}")
            resp = await self._client.get(path, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("market")
            logger.warning(
                "rest_market_error",
                ticker=ticker,
                status=resp.status_code,
            )
        except Exception:
            logger.exception("rest_market_failed", ticker=ticker)
        return None

    async def get_event(self, event_ticker: str) -> dict | None:
        """Fetch event data by event_ticker. Returns None on failure."""
        path = f"/events/{event_ticker}"
        try:
            headers = self._generate_rest_headers("GET", f"/trade-api/v2{path}")
            resp = await self._client.get(path, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("event")
            logger.warning(
                "rest_event_error",
                event_ticker=event_ticker,
                status=resp.status_code,
            )
        except Exception:
            logger.exception("rest_event_failed", event_ticker=event_ticker)
        return None

    async def get_series(self, series_ticker: str) -> dict | None:
        """Fetch series data by series_ticker. Returns None on failure."""
        path = f"/series/{series_ticker}"
        try:
            headers = self._generate_rest_headers("GET", f"/trade-api/v2{path}")
            resp = await self._client.get(path, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("series")
            logger.warning(
                "rest_series_error",
                series_ticker=series_ticker,
                status=resp.status_code,
            )
        except Exception:
            logger.exception("rest_series_failed", series_ticker=series_ticker)
        return None

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()
