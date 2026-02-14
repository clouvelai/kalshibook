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


class ApiKeyCreated(BaseModel):
    """Response after creating an API key (raw key shown once)."""

    id: str
    key: str = Field(description="Raw API key — shown ONCE, store it securely")
    name: str
    key_prefix: str
    created_at: str


class ApiKeyInfo(BaseModel):
    """Info about an existing API key (raw key NOT included)."""

    id: str
    name: str
    key_prefix: str
    created_at: str
    last_used_at: str | None = None


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
