"""Response models for KalshiBook API data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from kalshibook._parsing import parse_datetime


# ---------------------------------------------------------------------------
# Response metadata (attached to every API response)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ResponseMeta:
    """Credit and request metadata extracted from API response headers/body."""

    credits_used: int
    credits_remaining: int
    response_time: float
    request_id: str

    @classmethod
    def from_headers(cls, headers: dict, body: dict) -> ResponseMeta:
        """Parse metadata from httpx response headers and body.

        Uses -1 as sentinel for missing credit headers (e.g. on error responses).
        """
        return cls(
            credits_used=int(headers.get("x-credits-cost", -1)),
            credits_remaining=int(headers.get("x-credits-remaining", -1)),
            response_time=float(body.get("response_time", 0.0)),
            request_id=str(body.get("request_id", "")),
        )


# ---------------------------------------------------------------------------
# Orderbook models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class OrderbookLevel:
    """A single price level in the orderbook."""

    price: int
    quantity: int

    @classmethod
    def from_dict(cls, data: dict) -> OrderbookLevel:
        return cls(
            price=data["price"],
            quantity=data["quantity"],
        )


@dataclass(slots=True, frozen=True)
class OrderbookResponse:
    """Reconstructed orderbook state at a specific timestamp."""

    market_ticker: str
    timestamp: datetime
    snapshot_basis: datetime
    deltas_applied: int
    yes: list[OrderbookLevel]
    no: list[OrderbookLevel]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> OrderbookResponse:
        return cls(
            market_ticker=data["market_ticker"],
            timestamp=parse_datetime(data["timestamp"]),  # type: ignore[arg-type]
            snapshot_basis=parse_datetime(data["snapshot_basis"]),  # type: ignore[arg-type]
            deltas_applied=data["deltas_applied"],
            yes=[OrderbookLevel.from_dict(lv) for lv in data.get("yes", [])],
            no=[OrderbookLevel.from_dict(lv) for lv in data.get("no", [])],
            meta=meta,
        )


# ---------------------------------------------------------------------------
# Delta models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class DeltaRecord:
    """A single orderbook delta event."""

    market_ticker: str
    ts: datetime
    seq: int
    price_cents: int
    delta_amount: int
    side: str

    @classmethod
    def from_dict(cls, data: dict) -> DeltaRecord:
        return cls(
            market_ticker=data["market_ticker"],
            ts=parse_datetime(data["ts"]),  # type: ignore[arg-type]
            seq=data["seq"],
            price_cents=data["price_cents"],
            delta_amount=data["delta_amount"],
            side=data["side"],
        )


@dataclass(slots=True, frozen=True)
class DeltasResponse:
    """Paginated list of orderbook deltas."""

    data: list[DeltaRecord]
    next_cursor: str | None
    has_more: bool
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> DeltasResponse:
        return cls(
            data=[DeltaRecord.from_dict(d) for d in data.get("data", [])],
            next_cursor=data.get("next_cursor"),
            has_more=data.get("has_more", False),
            meta=meta,
        )


# ---------------------------------------------------------------------------
# Trade models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class TradeRecord:
    """A single trade record."""

    trade_id: str
    market_ticker: str
    yes_price: int
    no_price: int
    count: int
    taker_side: str
    ts: datetime

    @classmethod
    def from_dict(cls, data: dict) -> TradeRecord:
        return cls(
            trade_id=data["trade_id"],
            market_ticker=data["market_ticker"],
            yes_price=data["yes_price"],
            no_price=data["no_price"],
            count=data["count"],
            taker_side=data["taker_side"],
            ts=parse_datetime(data["ts"]),  # type: ignore[arg-type]
        )


@dataclass(slots=True, frozen=True)
class TradesResponse:
    """Paginated list of trades."""

    data: list[TradeRecord]
    next_cursor: str | None
    has_more: bool
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> TradesResponse:
        return cls(
            data=[TradeRecord.from_dict(d) for d in data.get("data", [])],
            next_cursor=data.get("next_cursor"),
            has_more=data.get("has_more", False),
            meta=meta,
        )
