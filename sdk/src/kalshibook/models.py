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


# ---------------------------------------------------------------------------
# Market models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class MarketSummary:
    """Summary info for a market."""

    ticker: str
    title: str | None
    event_ticker: str | None
    status: str
    category: str | None
    first_data_at: datetime | None
    last_data_at: datetime | None

    @classmethod
    def from_dict(cls, data: dict) -> MarketSummary:
        return cls(
            ticker=data["ticker"],
            title=data.get("title"),
            event_ticker=data.get("event_ticker"),
            status=data["status"],
            category=data.get("category"),
            first_data_at=parse_datetime(data.get("first_data_at")),
            last_data_at=parse_datetime(data.get("last_data_at")),
        )


@dataclass(slots=True, frozen=True)
class MarketDetail:
    """Full detail for a single market (flat, no inheritance)."""

    ticker: str
    title: str | None
    event_ticker: str | None
    status: str
    category: str | None
    first_data_at: datetime | None
    last_data_at: datetime | None
    rules: str | None
    strike_price: float | None
    discovered_at: datetime
    metadata: dict | None
    snapshot_count: int
    delta_count: int

    @classmethod
    def from_dict(cls, data: dict) -> MarketDetail:
        return cls(
            ticker=data["ticker"],
            title=data.get("title"),
            event_ticker=data.get("event_ticker"),
            status=data["status"],
            category=data.get("category"),
            first_data_at=parse_datetime(data.get("first_data_at")),
            last_data_at=parse_datetime(data.get("last_data_at")),
            rules=data.get("rules"),
            strike_price=data.get("strike_price"),
            discovered_at=parse_datetime(data["discovered_at"]),  # type: ignore[arg-type]
            metadata=data.get("metadata"),
            snapshot_count=data["snapshot_count"],
            delta_count=data["delta_count"],
        )


@dataclass(slots=True, frozen=True)
class MarketsResponse:
    """List of markets."""

    data: list[MarketSummary]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> MarketsResponse:
        return cls(
            data=[MarketSummary.from_dict(m) for m in data.get("data", [])],
            meta=meta,
        )


@dataclass(slots=True, frozen=True)
class MarketDetailResponse:
    """Single market detail."""

    data: MarketDetail
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> MarketDetailResponse:
        return cls(
            data=MarketDetail.from_dict(data["data"]),
            meta=meta,
        )


# ---------------------------------------------------------------------------
# Candle models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class CandleRecord:
    """OHLCV candle for a market."""

    bucket: datetime
    market_ticker: str
    open: int
    high: int
    low: int
    close: int
    volume: int
    trade_count: int

    @classmethod
    def from_dict(cls, data: dict) -> CandleRecord:
        return cls(
            bucket=parse_datetime(data["bucket"]),  # type: ignore[arg-type]
            market_ticker=data["market_ticker"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"],
            trade_count=data["trade_count"],
        )


@dataclass(slots=True, frozen=True)
class CandlesResponse:
    """List of OHLCV candles."""

    data: list[CandleRecord]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> CandlesResponse:
        return cls(
            data=[CandleRecord.from_dict(c) for c in data.get("data", [])],
            meta=meta,
        )


# ---------------------------------------------------------------------------
# Settlement models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SettlementRecord:
    """Settlement result for a market."""

    market_ticker: str
    event_ticker: str | None
    result: str | None
    settlement_value: int | None
    determined_at: datetime | None
    settled_at: datetime | None

    @classmethod
    def from_dict(cls, data: dict) -> SettlementRecord:
        return cls(
            market_ticker=data["market_ticker"],
            event_ticker=data.get("event_ticker"),
            result=data.get("result"),
            settlement_value=data.get("settlement_value"),
            determined_at=parse_datetime(data.get("determined_at")),
            settled_at=parse_datetime(data.get("settled_at")),
        )


@dataclass(slots=True, frozen=True)
class SettlementResponse:
    """Single settlement result."""

    data: SettlementRecord
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> SettlementResponse:
        return cls(
            data=SettlementRecord.from_dict(data["data"]),
            meta=meta,
        )


@dataclass(slots=True, frozen=True)
class SettlementsResponse:
    """List of settlement results."""

    data: list[SettlementRecord]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> SettlementsResponse:
        return cls(
            data=[SettlementRecord.from_dict(s) for s in data.get("data", [])],
            meta=meta,
        )


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class EventSummary:
    """Summary info for an event."""

    event_ticker: str
    series_ticker: str | None
    title: str | None
    sub_title: str | None
    category: str | None
    mutually_exclusive: bool | None
    status: str | None
    market_count: int | None

    @classmethod
    def from_dict(cls, data: dict) -> EventSummary:
        return cls(
            event_ticker=data["event_ticker"],
            series_ticker=data.get("series_ticker"),
            title=data.get("title"),
            sub_title=data.get("sub_title"),
            category=data.get("category"),
            mutually_exclusive=data.get("mutually_exclusive"),
            status=data.get("status"),
            market_count=data.get("market_count"),
        )


@dataclass(slots=True, frozen=True)
class EventDetail:
    """Full event detail including child markets (flat, no inheritance)."""

    event_ticker: str
    series_ticker: str | None
    title: str | None
    sub_title: str | None
    category: str | None
    mutually_exclusive: bool | None
    status: str | None
    market_count: int | None
    markets: list[MarketSummary]

    @classmethod
    def from_dict(cls, data: dict) -> EventDetail:
        return cls(
            event_ticker=data["event_ticker"],
            series_ticker=data.get("series_ticker"),
            title=data.get("title"),
            sub_title=data.get("sub_title"),
            category=data.get("category"),
            mutually_exclusive=data.get("mutually_exclusive"),
            status=data.get("status"),
            market_count=data.get("market_count"),
            markets=[MarketSummary.from_dict(m) for m in data.get("markets", [])],
        )


@dataclass(slots=True, frozen=True)
class EventsResponse:
    """List of events."""

    data: list[EventSummary]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> EventsResponse:
        return cls(
            data=[EventSummary.from_dict(e) for e in data.get("data", [])],
            meta=meta,
        )


@dataclass(slots=True, frozen=True)
class EventDetailResponse:
    """Single event with full detail."""

    data: EventDetail
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> EventDetailResponse:
        return cls(
            data=EventDetail.from_dict(data["data"]),
            meta=meta,
        )


# ---------------------------------------------------------------------------
# Billing models
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class BillingStatus:
    """Current billing account status."""

    tier: str
    credits_total: int
    credits_used: int
    credits_remaining: int
    payg_enabled: bool
    billing_cycle_start: datetime

    @classmethod
    def from_dict(cls, data: dict) -> BillingStatus:
        return cls(
            tier=data["tier"],
            credits_total=data["credits_total"],
            credits_used=data["credits_used"],
            credits_remaining=data["credits_remaining"],
            payg_enabled=data["payg_enabled"],
            billing_cycle_start=parse_datetime(data["billing_cycle_start"]),  # type: ignore[arg-type]
        )
