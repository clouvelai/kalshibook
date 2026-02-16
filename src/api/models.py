"""Pydantic v2 request and response models for the KalshiBook API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class OrderbookRequest(BaseModel):
    """Request to reconstruct orderbook state at a specific timestamp."""

    market_ticker: str = Field(description="Kalshi market ticker")
    timestamp: datetime = Field(description="ISO 8601 timestamp to reconstruct the orderbook at")
    depth: int | None = Field(
        default=None, description="Limit number of price levels returned (default: all)"
    )


class DeltasRequest(BaseModel):
    """Request to query raw orderbook deltas for a market and time range."""

    market_ticker: str = Field(description="Kalshi market ticker")
    start_time: datetime = Field(description="Start of time range (ISO 8601)")
    end_time: datetime = Field(description="End of time range (ISO 8601)")
    cursor: str | None = Field(default=None, description="Pagination cursor from previous response")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of results per page")


# ---------------------------------------------------------------------------
# Response models — Orderbook
# ---------------------------------------------------------------------------

class OrderbookLevel(BaseModel):
    """A single price level in the orderbook."""

    price: int = Field(description="Price in cents (1-99)")
    quantity: int = Field(description="Total contracts at this price level")


class OrderbookResponse(BaseModel):
    """Reconstructed orderbook state at a specific timestamp."""

    market_ticker: str = Field(description="Kalshi market ticker")
    timestamp: str = Field(description="Orderbook state as-of this ISO 8601 timestamp")
    snapshot_basis: str = Field(
        description="ISO 8601 timestamp of the underlying snapshot used for reconstruction"
    )
    deltas_applied: int = Field(description="Number of deltas applied to reach this state")
    yes: list[OrderbookLevel] = Field(description="Yes side levels, sorted by price descending")
    no: list[OrderbookLevel] = Field(description="No side levels, sorted by price descending")
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Response models — Deltas
# ---------------------------------------------------------------------------

class DeltaRecord(BaseModel):
    """A single orderbook delta event."""

    market_ticker: str
    ts: str = Field(description="ISO 8601 timestamp of the delta")
    seq: int = Field(description="Sequence number for ordering")
    price_cents: int = Field(description="Price level in cents")
    delta_amount: int = Field(description="Change in quantity (positive or negative)")
    side: str = Field(description="'yes' or 'no'")


class DeltasResponse(BaseModel):
    """Paginated list of orderbook deltas."""

    data: list[DeltaRecord]
    next_cursor: str | None = Field(description="Cursor for next page, null if no more results")
    has_more: bool
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Response models — Markets
# ---------------------------------------------------------------------------

class MarketSummary(BaseModel):
    """Summary info for a market."""

    ticker: str
    title: str | None = None
    event_ticker: str | None = None
    status: str
    category: str | None = None
    first_data_at: str | None = Field(
        default=None, description="Earliest data available (ISO 8601)"
    )
    last_data_at: str | None = Field(default=None, description="Latest data available (ISO 8601)")


class MarketDetail(MarketSummary):
    """Full detail for a single market, including metadata and data counts."""

    rules: str | None = None
    strike_price: float | None = None
    discovered_at: str
    metadata: dict | None = None
    snapshot_count: int
    delta_count: int


class MarketsResponse(BaseModel):
    """List of markets."""

    data: list[MarketSummary]
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


class MarketDetailResponse(BaseModel):
    """Single market detail."""

    data: MarketDetail
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Auth / API key models
# ---------------------------------------------------------------------------

class ApiKeyCreate(BaseModel):
    """Request to create a new API key."""

    name: str = Field(default="Default", max_length=100)
    key_type: str = Field(default="dev", description="Key type: 'dev' or 'prod'")


class ApiKeyUpdate(BaseModel):
    """Request to update an existing API key."""

    name: str | None = Field(default=None, max_length=100)
    key_type: str | None = Field(default=None, description="Key type: 'dev' or 'prod'")


class ApiKeyCreated(BaseModel):
    """Response after creating an API key (raw key shown once)."""

    id: str
    key: str = Field(description="Raw API key — shown ONCE, store it securely")
    name: str
    key_prefix: str
    key_type: str = Field(default="dev", description="Key type: 'dev' or 'prod'")
    created_at: str


class ApiKeyInfo(BaseModel):
    """Info about an existing API key (raw key NOT included)."""

    id: str
    name: str
    key_prefix: str
    key_type: str = Field(default="dev", description="Key type: 'dev' or 'prod'")
    created_at: str
    last_used_at: str | None = None


class KeyUsageItem(BaseModel):
    """Per-key usage info with aggregated credits for the current billing cycle."""

    id: str
    name: str
    key_prefix: str
    key_type: str
    created_at: str
    last_used_at: str | None = None
    credits_used: int = Field(description="Credits consumed by this key in the current billing cycle")


class KeysUsageResponse(BaseModel):
    """Per-key usage aggregation response."""

    data: list[KeyUsageItem]
    request_id: str


class ApiKeysResponse(BaseModel):
    """List of API keys for a user."""

    data: list[ApiKeyInfo]
    request_id: str


class ApiKeyCreatedResponse(BaseModel):
    """Response wrapping a newly created API key."""

    data: ApiKeyCreated
    request_id: str


class SignupRequest(BaseModel):
    """Request to create a new user account."""

    email: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Request to log in with email and password."""

    email: str
    password: str


class AuthResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str
    refresh_token: str
    user_id: str
    request_id: str


# ---------------------------------------------------------------------------
# Billing models
# ---------------------------------------------------------------------------


class BillingStatusResponse(BaseModel):
    """Current billing account status."""

    tier: str = Field(description="Billing tier: free, payg, or project")
    credits_total: int = Field(description="Total credits allocated for the billing cycle")
    credits_used: int = Field(description="Credits consumed in the current billing cycle")
    credits_remaining: int = Field(description="Credits remaining (total - used)")
    payg_enabled: bool = Field(description="Whether Pay-As-You-Go is enabled")
    billing_cycle_start: str = Field(description="Start of current billing cycle (ISO 8601)")
    request_id: str


class PaygToggleRequest(BaseModel):
    """Request to enable or disable Pay-As-You-Go billing."""

    enable: bool = Field(description="True to enable PAYG, False to disable")


class PaygToggleResponse(BaseModel):
    """Response after toggling PAYG status."""

    payg_enabled: bool = Field(description="Current PAYG status after toggle")
    message: str = Field(description="Human-readable status message")
    request_id: str


class CheckoutResponse(BaseModel):
    """Response with a Stripe Checkout Session URL."""

    checkout_url: str = Field(description="Stripe Checkout URL — redirect user here")
    request_id: str


class PortalResponse(BaseModel):
    """Response with a Stripe Customer Portal URL."""

    portal_url: str = Field(description="Stripe Customer Portal URL for subscription management")
    request_id: str


# ---------------------------------------------------------------------------
# Response models — Trades
# ---------------------------------------------------------------------------

class TradesRequest(BaseModel):
    """Request to query trades for a market and time range."""

    market_ticker: str = Field(description="Kalshi market ticker")
    start_time: datetime = Field(description="Start of time range (ISO 8601)")
    end_time: datetime = Field(description="End of time range (ISO 8601)")
    cursor: str | None = Field(default=None, description="Pagination cursor from previous response")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of results per page")


class TradeRecord(BaseModel):
    """A single trade record."""

    trade_id: str = Field(description="Unique trade identifier")
    market_ticker: str = Field(description="Kalshi market ticker")
    yes_price: int = Field(description="Yes-side price in cents")
    no_price: int = Field(description="No-side price in cents")
    count: int = Field(description="Number of contracts traded")
    taker_side: str = Field(description="'yes' or 'no'")
    ts: str = Field(description="ISO 8601 timestamp of the trade")


class TradesResponse(BaseModel):
    """Paginated list of trades."""

    data: list[TradeRecord]
    next_cursor: str | None = Field(description="Cursor for next page, null if no more results")
    has_more: bool
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Response models — Settlements
# ---------------------------------------------------------------------------

class SettlementRecord(BaseModel):
    """Settlement result for a market."""

    market_ticker: str = Field(description="Kalshi market ticker")
    event_ticker: str | None = Field(default=None, description="Parent event ticker")
    result: str | None = Field(default=None, description="Settlement result: yes, no, all_no, all_yes, or void")
    settlement_value: int | None = Field(default=None, description="Settlement value in cents")
    determined_at: str | None = Field(default=None, description="When result was determined (ISO 8601)")
    settled_at: str | None = Field(default=None, description="When settlement was finalized (ISO 8601)")


class SettlementResponse(BaseModel):
    """Single settlement result."""

    data: SettlementRecord
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


class SettlementsResponse(BaseModel):
    """List of settlement results."""

    data: list[SettlementRecord]
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Response models — Candles
# ---------------------------------------------------------------------------

class CandleRecord(BaseModel):
    """OHLCV candle for a market."""

    bucket: str = Field(description="Candle period start (ISO 8601)")
    market_ticker: str = Field(description="Kalshi market ticker")
    open: int = Field(description="Opening price in cents")
    high: int = Field(description="Highest price in cents")
    low: int = Field(description="Lowest price in cents")
    close: int = Field(description="Closing price in cents")
    volume: int = Field(description="Total contracts traded")
    trade_count: int = Field(description="Number of individual trades")


class CandlesResponse(BaseModel):
    """List of OHLCV candles."""

    data: list[CandleRecord]
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Response models — Events / Hierarchy
# ---------------------------------------------------------------------------

class EventSummary(BaseModel):
    """Summary info for an event."""

    event_ticker: str = Field(description="Unique event ticker")
    series_ticker: str | None = Field(default=None, description="Parent series ticker")
    title: str | None = Field(default=None, description="Event title")
    sub_title: str | None = Field(default=None, description="Event subtitle")
    category: str | None = Field(default=None, description="Event category")
    mutually_exclusive: bool | None = Field(default=None, description="Whether markets are mutually exclusive")
    status: str | None = Field(default=None, description="Event status")
    market_count: int | None = Field(default=None, description="Number of markets in this event")


class EventDetail(EventSummary):
    """Full event detail including child markets."""

    markets: list[MarketSummary] = Field(description="Markets belonging to this event")


class EventsResponse(BaseModel):
    """List of events."""

    data: list[EventSummary]
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


class EventDetailResponse(BaseModel):
    """Single event with full detail."""

    data: EventDetail
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


class SeriesRecord(BaseModel):
    """Summary info for a series."""

    ticker: str = Field(description="Unique series ticker")
    title: str | None = Field(default=None, description="Series title")
    frequency: str | None = Field(default=None, description="Release frequency")
    category: str | None = Field(default=None, description="Series category")


class SeriesResponse(BaseModel):
    """List of series."""

    data: list[SeriesRecord]
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")


# ---------------------------------------------------------------------------
# Error models (for OpenAPI spec documentation)
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Machine-readable error detail."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    status: int = Field(description="HTTP status code")


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail
    request_id: str
