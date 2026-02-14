"""Kalshi WebSocket connection manager with auth and automatic reconnection."""

from __future__ import annotations

import asyncio
import base64
import random
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import orjson
import websockets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from src.collector.metrics import get_logger, get_metrics
from src.shared.config import Settings

logger = get_logger("connection")


def load_private_key_from_path(path: str):
    """Load RSA private key from PEM file."""
    key_data = Path(path).read_bytes()
    return serialization.load_pem_private_key(key_data, password=None)


def load_private_key_from_content(content: str):
    """Load RSA private key from inline PEM string."""
    return serialization.load_pem_private_key(content.encode(), password=None)


def load_private_key(settings: Settings):
    """Load RSA private key from file path or inline content."""
    if settings.kalshi_private_key_content:
        return load_private_key_from_content(settings.kalshi_private_key_content)
    if settings.kalshi_private_key_path:
        return load_private_key_from_path(settings.kalshi_private_key_path)
    raise ValueError("Set KALSHI_PRIVATE_KEY_CONTENT or KALSHI_PRIVATE_KEY_PATH")


def generate_auth_headers(api_key: str, private_key, ws_path: str) -> dict[str, str]:
    """Generate Kalshi WS authentication headers using RSA-PSS."""
    timestamp_ms = str(int(time.time() * 1000))
    message = timestamp_ms + "GET" + ws_path
    signature = private_key.sign(
        message.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": api_key,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode(),
        "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
    }


class KalshiWSConnection:
    """Manages a persistent WebSocket connection to Kalshi with auto-reconnection."""

    def __init__(
        self,
        settings: Settings,
        on_message: Callable[[dict], Awaitable[None]],
        on_reconnect: Callable[[], Awaitable[None]],
    ):
        self._settings = settings
        self._on_message = on_message
        self._on_reconnect = on_reconnect
        self._ws: websockets.ClientConnection | None = None
        self._private_key = None
        self._metrics = get_metrics()
        self._running = False
        self._cmd_id = 0

    async def start(self) -> None:
        """Start the connection loop with automatic reconnection."""
        self._private_key = load_private_key(self._settings)
        self._running = True

        backoff = 1.0
        max_backoff = 60.0

        while self._running:
            try:
                await self._connect_and_run()
                backoff = 1.0  # Reset on clean disconnect
            except (
                websockets.ConnectionClosed,
                websockets.InvalidStatusCode,
                OSError,
                ConnectionError,
            ) as exc:
                self._metrics.record_disconnected()
                logger.warning(
                    "ws_disconnected",
                    error=str(exc),
                    backoff_seconds=backoff,
                )
                if not self._running:
                    break
                self._metrics.record_reconnecting()
                # Exponential backoff with jitter
                jitter = random.uniform(0, backoff * 0.3)
                await asyncio.sleep(backoff + jitter)
                backoff = min(backoff * 2, max_backoff)

    async def _connect_and_run(self) -> None:
        """Establish connection and process messages."""
        headers = generate_auth_headers(
            self._settings.kalshi_api_key_id,
            self._private_key,
            self._settings.kalshi_ws_path,
        )
        logger.info("ws_connecting", url=self._settings.kalshi_ws_url)

        async with websockets.connect(
            self._settings.kalshi_ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self._ws = ws
            self._metrics.record_connected()
            logger.info("ws_connected")

            # Trigger reconnect handler to resubscribe channels
            await self._on_reconnect()

            # Message processing loop with watchdog
            watchdog_timeout = self._settings.watchdog_timeout_seconds
            while self._running:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=watchdog_timeout)
                    self._metrics.record_message()
                    msg = orjson.loads(raw)
                    await self._on_message(msg)
                except asyncio.TimeoutError:
                    # Watchdog: no message in N seconds, check if connection is alive
                    logger.warning("ws_watchdog_timeout", timeout_s=watchdog_timeout)
                    # Send a ping to check - if it fails, websockets will raise
                    await ws.ping()

    async def send_subscribe(
        self, channels: list[str], market_tickers: list[str] | None = None
    ) -> int:
        """Send a subscribe command. Returns the command ID."""
        return await self._send_command("subscribe", channels, market_tickers)

    async def send_unsubscribe(
        self, channels: list[str], market_tickers: list[str] | None = None
    ) -> int:
        """Send an unsubscribe command. Returns the command ID."""
        return await self._send_command("unsubscribe", channels, market_tickers)

    async def _send_command(
        self,
        cmd_type: str,
        channels: list[str],
        market_tickers: list[str] | None = None,
    ) -> int:
        """Send a subscribe/unsubscribe command. Returns the command ID."""
        self._cmd_id += 1
        cmd: dict = {
            "id": self._cmd_id,
            "cmd": cmd_type,
            "params": {"channels": channels},
        }
        if market_tickers:
            cmd["params"]["market_tickers"] = market_tickers
        await self._send(cmd)
        logger.debug(
            f"ws_{cmd_type}_sent",
            cmd_id=self._cmd_id,
            channels=channels,
            tickers_count=len(market_tickers) if market_tickers else 0,
        )
        return self._cmd_id

    async def _send(self, data: dict) -> None:
        """Send JSON data over the websocket."""
        if self._ws is None:
            raise RuntimeError("WebSocket not connected")
        await self._ws.send(orjson.dumps(data))

    async def stop(self) -> None:
        """Stop the connection loop gracefully."""
        self._running = False
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        logger.info("ws_stopped")

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._ws.state.name == "OPEN"
