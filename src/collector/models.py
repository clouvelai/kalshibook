"""Data models for Kalshi websocket messages and internal state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# --- Kalshi WS message models ---


@dataclass(frozen=True, slots=True)
class OrderbookSnapshot:
    """Parsed orderbook_snapshot message from Kalshi WS."""

    market_ticker: str
    seq: int
    sid: int
    yes: list[list[int]]  # [[price_cents, quantity], ...]
    no: list[list[int]]  # [[price_cents, quantity], ...]
    ts: datetime


@dataclass(frozen=True, slots=True)
class OrderbookDelta:
    """Parsed orderbook_delta message from Kalshi WS."""

    market_ticker: str
    seq: int
    sid: int
    price: int  # price in cents
    delta: int  # signed quantity change
    side: str  # "yes" or "no"
    ts: datetime


# --- Internal state models ---


@dataclass
class MarketSubscription:
    """Tracks subscription state for a single market."""

    ticker: str
    sid: int = 0
    last_seq: int = -1
    subscribed_at: datetime | None = None
    is_stale: bool = False


@dataclass
class GapRecord:
    """Record of a detected sequence gap."""

    market_ticker: str
    detected_at: datetime
    expected_seq: int
    received_seq: int
    sid: int


@dataclass
class OverflowRecord:
    """Record of a market that couldn't be subscribed due to cap."""

    market_ticker: str
    event_ticker: str = ""
    reason: str = "cap_reached"
