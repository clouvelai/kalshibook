# Architecture Research: Python SDK for KalshiBook API

**Domain:** Python SDK wrapping a financial data REST API with high-level backtesting abstractions
**Researched:** 2026-02-17
**Confidence:** HIGH (patterns verified against Polygon.io, Alpaca, Stripe, Azure SDK guidelines, and existing KalshiBook API source code)

## System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     SDK PACKAGE (kalshibook)                              │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    HIGH-LEVEL ABSTRACTIONS                          │  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌────────────────┐  │  │
│  │  │  replay_orderbook │  │  stream_trades    │  │  discover      │  │  │
│  │  │  (snapshot+delta  │  │  (auto-paginate   │  │  (markets,     │  │  │
│  │  │   reconstruction) │  │   trade history)  │  │   events,      │  │  │
│  │  │                   │  │                   │  │   coverage)    │  │  │
│  │  └───────┬───────────┘  └───────┬───────────┘  └───────┬────────┘  │  │
│  │          │                      │                      │           │  │
│  ├──────────┴──────────────────────┴──────────────────────┴───────────┤  │
│  │                                                                    │  │
│  │                    LOW-LEVEL CLIENT LAYER                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │  │
│  │  │  KalshiBook  │  │  Pagination  │  │  Error Mapping           │ │  │
│  │  │  Client      │  │  Iterator    │  │  (HTTP -> exceptions)    │ │  │
│  │  │  (httpx)     │  │  (async gen) │  │                          │ │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘ │  │
│  │         │                 │                      │                 │  │
│  ├─────────┴─────────────────┴──────────────────────┴─────────────────┤  │
│  │                                                                    │  │
│  │                    MODELS LAYER                                    │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐ │  │
│  │  │  Request        │  │  Response       │  │  Domain (Orderbook, │ │  │
│  │  │  dataclasses    │  │  dataclasses    │  │  Delta, Trade, etc) │ │  │
│  │  └────────────────┘  └────────────────┘  └──────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                               httpx (HTTP)                               │
│                                    │                                     │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
                                     ↓
┌────────────────────────────────────────────────────────────────────────────┐
│                     KALSHIBOOK API (existing)                              │
│  POST /orderbook  POST /deltas  POST /trades  GET /markets  GET /candles  │
│  GET /events  GET /settlements  GET /markets/{ticker}                      │
│  Auth: Authorization: Bearer kb-...   Errors: {"error": {...}, "req_id"}  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| KalshiBookClient | Single entry point: auth, HTTP transport, method dispatch | httpx.AsyncClient with connection pooling |
| Pagination Iterator | Auto-paginate cursor-based endpoints transparently | `async for` generator yielding individual records |
| Error Mapping | Map HTTP status codes + error.code to typed exceptions | Exception hierarchy mirroring server's KalshiBookError tree |
| Request Models | Type-safe request construction with defaults | Python dataclasses (not Pydantic -- SDK should be lightweight) |
| Response Models | Structured response parsing with attribute access | Python dataclasses with `from_dict()` class methods |
| Domain Models | Orderbook, OrderbookLevel for reconstruction state | Dataclasses with `apply_delta()` mutation methods |
| replay_orderbook | Fetch snapshot + auto-paginate deltas, reconstruct evolving state | Async generator yielding (timestamp, Orderbook) tuples |
| stream_trades | Auto-paginate trade history for a time range | Async generator yielding Trade records |
| discover | List markets, events, coverage dates | Sync convenience wrappers over list endpoints |

## Repository Strategy: Monorepo with uv Workspace

**Decision: Keep the SDK in the same repository as the API, using uv workspaces.**

The project already uses `uv` for package management. uv workspaces (inspired by Cargo workspaces) allow multiple Python packages in a single repository with a shared lockfile.

### Why Monorepo

1. **Atomic changes:** API model changes + SDK model updates in one PR. When `OrderbookResponse` adds a field on the server, the SDK model updates in the same commit.
2. **Test against real API:** SDK integration tests can spin up the FastAPI app directly (import `src.api.main:app`) without deploying anywhere.
3. **Shared lockfile:** uv workspace creates one `uv.lock` for the whole repo, preventing dependency conflicts between API and SDK.
4. **Already using uv:** No new tooling to learn. The project's existing `pyproject.toml` and `uv.lock` extend naturally.
5. **Separate publishing:** SDK publishes to PyPI independently. Users install `pip install kalshibook` without the server code.

### Why NOT Separate Repo

- Two-repo coordination overhead (SDK lags behind API changes)
- Can't run SDK integration tests against the API without deploying a staging environment
- Model duplication with no enforcement mechanism to keep them in sync
- For a solo developer / small team, the coordination tax is high and the benefits (independent CI, independent versioning) don't outweigh the cost

### uv Workspace Configuration

Root `pyproject.toml` adds:
```toml
[tool.uv.workspace]
members = ["sdk"]
```

SDK lives at `sdk/` with its own `pyproject.toml`:
```toml
[project]
name = "kalshibook"
version = "0.1.0"
description = "Python SDK for KalshiBook L2 orderbook data API"
requires-python = ">=3.10"
dependencies = ["httpx>=0.27"]

[project.optional-dependencies]
pandas = ["pandas>=2.0"]
```

## Recommended Project Structure

```
kalshibook/                          # Repository root (existing)
├── pyproject.toml                   # Server app (existing, adds [tool.uv.workspace])
├── uv.lock                         # Shared lockfile (existing)
├── src/                             # Server code (existing, unchanged)
│   ├── api/
│   ├── collector/
│   └── shared/
├── sdk/                             # NEW — SDK package
│   ├── pyproject.toml               # SDK-specific deps and metadata
│   ├── src/
│   │   └── kalshibook/              # Import: from kalshibook import KalshiBook
│   │       ├── __init__.py          # Public API: KalshiBook, exceptions, models
│   │       ├── client.py            # KalshiBook class (single client, all methods)
│   │       ├── models.py            # All request/response/domain dataclasses
│   │       ├── exceptions.py        # Exception hierarchy
│   │       ├── _pagination.py       # Auto-pagination iterator (private)
│   │       ├── _http.py             # HTTP transport layer (private)
│   │       └── replay.py            # High-level: replay_orderbook, stream_trades
│   ├── tests/
│   │   ├── test_client.py           # Unit tests (mocked HTTP)
│   │   ├── test_models.py           # Model serialization/deserialization
│   │   ├── test_pagination.py       # Pagination iterator behavior
│   │   ├── test_replay.py           # Replay abstraction tests
│   │   └── test_integration.py      # Integration tests against real API
│   └── examples/
│       ├── quickstart.py            # Basic usage
│       ├── replay_orderbook.py      # Orderbook replay example
│       └── backtest_strategy.py     # Full backtesting example
├── tests/                           # Server tests (existing)
└── dashboard/                       # Next.js dashboard (existing)
```

### Structure Rationale

- **Flat module layout (not nested packages):** The SDK has ~10 endpoints and ~15 models. A flat structure (`kalshibook/client.py`, not `kalshibook/resources/orderbook/client.py`) is appropriate. Polygon.io uses flat structure for a similarly-scoped SDK. Nested packages make sense for huge APIs (Stripe, Azure) but add import complexity for small APIs.
- **Single `models.py`:** All dataclasses in one file. The API has ~15 response models and ~5 request models -- this fits comfortably in one file (~300 lines). Split only when it exceeds ~500 lines.
- **Private modules with underscore prefix:** `_pagination.py` and `_http.py` are implementation details. Users import from `kalshibook`, not from `kalshibook._http`.
- **`replay.py` as separate module:** The high-level abstractions (`replay_orderbook`, `stream_trades`) are distinct from the low-level client methods. They compose multiple client calls and contain domain logic (orderbook reconstruction). Separating them keeps `client.py` focused on 1:1 endpoint mapping.
- **`sdk/` directory at repo root:** Clean separation from server code. uv workspace member. Published to PyPI independently. Server code never imports from SDK; SDK never imports from server.

## Architectural Patterns

### Pattern 1: Single Client Class (Not Resource-Based)

**What:** One `KalshiBook` class with all methods, not separate `client.orderbook.get()` resource namespaces.

**When to use:** APIs with fewer than 20 endpoints. KalshiBook has 10 data endpoints.

**Why this over resource-based:** Resource-based clients (like `stripe.customers.create()`) make sense when you have hundreds of endpoints grouped into dozens of resources. For 10 endpoints, a single class gives simpler autocomplete, fewer imports, and a shallower learning curve.

**Trade-offs:**
- Pro: `client.get_orderbook()` is more discoverable than `client.orderbook.get()`
- Pro: No circular import issues between resource classes
- Pro: Simpler to maintain -- one file, one class
- Con: Class grows large if many endpoints are added (solve later by extracting mixins)

**Example:**
```python
from kalshibook import KalshiBook

client = KalshiBook(api_key="kb-...")

# Every endpoint is a direct method on the client
orderbook = await client.get_orderbook("TICKER-ABC", timestamp="2026-02-15T12:00:00Z")
markets = await client.list_markets()
trades = client.list_trades("TICKER-ABC", start_time=..., end_time=...)  # returns async iterator

# High-level abstractions are also methods on the client
async for ts, book in client.replay_orderbook("TICKER-ABC", start=..., end=...):
    print(f"{ts}: best_yes={book.best_yes}, best_no={book.best_no}")
```

### Pattern 2: Async-First with Sync Wrapper

**What:** All methods are `async def` by default. Provide a thin sync wrapper for users who don't want `asyncio`.

**When to use:** Always for modern Python SDKs that make HTTP calls.

**Why async-first:** The primary users (algo traders, quants) are building async trading systems. Orderbook replay iterates through thousands of paginated results -- async is dramatically more efficient here. httpx supports both sync and async natively.

**Trade-offs:**
- Pro: First-class async support for the primary use case
- Pro: httpx provides both sync and async clients, so one HTTP layer serves both
- Pro: Pagination and replay naturally express as async generators
- Con: Users unfamiliar with asyncio need to wrap in `asyncio.run()` or use sync client

**Example:**
```python
# Async (primary, recommended for replay/pagination)
import asyncio
from kalshibook import KalshiBook

async def main():
    async with KalshiBook(api_key="kb-...") as client:
        orderbook = await client.get_orderbook("TICKER", timestamp="...")

asyncio.run(main())

# Sync (convenience, wraps async internally)
from kalshibook import KalshiBook

client = KalshiBook(api_key="kb-...", sync=True)
orderbook = client.get_orderbook("TICKER", timestamp="...")
```

**Implementation:** The sync wrapper uses `httpx.Client` (sync) instead of `httpx.AsyncClient`. Detected at init time via `sync=True` flag. Internal methods check `self._sync` and dispatch accordingly. This avoids the `asyncio.run()` wrapper pattern which fails inside existing event loops.

### Pattern 3: Auto-Paginating Async Generator

**What:** Cursor-based endpoints return async generators that automatically fetch next pages as the user iterates.

**When to use:** All paginated endpoints (`/deltas`, `/trades`).

**Why generator, not list:** Delta queries can return millions of records. Loading all into memory defeats the purpose. An async generator fetches one page at a time, yielding individual records. The user sees a simple `async for` loop; the SDK handles cursor management internally.

**Trade-offs:**
- Pro: Constant memory usage regardless of result set size
- Pro: Clean API -- user writes `async for delta in client.list_deltas(...):`
- Pro: Can stop early without fetching remaining pages
- Con: Cannot `len()` the result or index into it (use `list()` to collect if needed)

**Example:**
```python
# Internal implementation
async def _auto_paginate(self, endpoint, request_data, record_cls):
    """Async generator that auto-paginates cursor-based endpoints."""
    cursor = None
    while True:
        if cursor:
            request_data["cursor"] = cursor
        response = await self._post(endpoint, request_data)
        for item in response["data"]:
            yield record_cls.from_dict(item)
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]

# User-facing
async for delta in client.list_deltas("TICKER", start_time=..., end_time=...):
    print(f"{delta.ts}: {delta.side} {delta.price_cents} x {delta.delta_amount}")

# Collect all if needed
all_deltas = [d async for d in client.list_deltas("TICKER", start_time=..., end_time=...)]
```

### Pattern 4: Exception Hierarchy Mirroring Server Errors

**What:** SDK exceptions map 1:1 to the server's error codes. The SDK inspects the `error.code` field in the JSON response and raises the corresponding typed exception.

**When to use:** Always. The server already returns structured errors with `code`, `message`, `status`.

**Trade-offs:**
- Pro: Users can catch specific errors: `except MarketNotFoundError`
- Pro: Exception carries the original error code, message, and request_id
- Pro: Mirrors the server's error taxonomy -- no translation layer to maintain
- Con: Adding new server error codes requires SDK update (acceptable since both are in monorepo)

**Example:**
```python
# SDK exception hierarchy
class KalshiBookError(Exception):
    """Base for all KalshiBook API errors."""
    def __init__(self, code: str, message: str, status: int, request_id: str):
        self.code = code
        self.message = message
        self.status = status
        self.request_id = request_id
        super().__init__(f"{code}: {message}")

class AuthenticationError(KalshiBookError): ...     # invalid_api_key (401)
class RateLimitError(KalshiBookError): ...           # rate_limit_exceeded (429)
class CreditsExhaustedError(KalshiBookError): ...    # credits_exhausted (429)
class MarketNotFoundError(KalshiBookError): ...      # market_not_found (404)
class EventNotFoundError(KalshiBookError): ...       # event_not_found (404)
class NoDataError(KalshiBookError): ...              # no_data_available (404)
class ValidationError(KalshiBookError): ...          # validation_error (422)

# Mapping (in _http.py)
_ERROR_MAP = {
    "invalid_api_key": AuthenticationError,
    "rate_limit_exceeded": RateLimitError,
    "credits_exhausted": CreditsExhaustedError,
    "market_not_found": MarketNotFoundError,
    "event_not_found": EventNotFoundError,
    "no_data_available": NoDataError,
    "validation_error": ValidationError,
}

def _raise_for_error(response_json, status_code):
    if "error" in response_json:
        err = response_json["error"]
        exc_cls = _ERROR_MAP.get(err["code"], KalshiBookError)
        raise exc_cls(
            code=err["code"],
            message=err["message"],
            status=err["status"],
            request_id=response_json.get("request_id", ""),
        )
```

## Data Flow

### Orderbook Replay Data Flow (Key Abstraction)

This is the most important data flow in the SDK. `replay_orderbook()` is the primary reason users install the SDK instead of calling the API directly.

```
client.replay_orderbook("TICKER", start="2026-02-15T10:00", end="2026-02-15T11:00")
    │
    │ Step 1: Fetch initial snapshot
    ↓
POST /orderbook  {"market_ticker": "TICKER", "timestamp": "2026-02-15T10:00:00Z"}
    │
    │ Response: OrderbookResponse with yes/no levels, snapshot_basis
    ↓
Build initial Orderbook state from yes/no levels
    │
    │ yield (start_timestamp, initial_orderbook)    ← user gets first state
    │
    │ Step 2: Auto-paginate deltas from snapshot_basis to end
    ↓
POST /deltas  {"market_ticker": "TICKER", "start_time": "2026-02-15T10:00:00Z",
               "end_time": "2026-02-15T11:00:00Z", "limit": 1000}
    │
    │ Page 1: 1000 deltas + next_cursor + has_more=true
    ↓
For each delta in page:
    │ Apply to in-memory Orderbook: book.apply_delta(delta)
    │ yield (delta.ts, orderbook_copy)              ← user gets evolved state
    │
    │ If has_more, fetch next page with cursor
    ↓
POST /deltas  {"market_ticker": "TICKER", ..., "cursor": "<next_cursor>"}
    │
    │ Page 2: 1000 deltas + next_cursor + has_more=true
    ↓
    ...repeat until has_more=false...
    │
    │ Generator exhausted — replay complete
    ↓
Done
```

### Key Design Decisions in Replay Flow

1. **Yield on every delta, not every N deltas:** Users building backtesting systems need every state transition. If they want sampling, they skip yields themselves.

2. **Yield copies vs references:** Yield a shallow copy of the orderbook on each delta. If we yield the same mutable object, users who store references see stale data. A shallow copy of `dict[int, int]` for yes/no books is cheap (~50-100 entries max for Kalshi binary markets).

3. **Use `/orderbook` for initial state, not manual snapshot+delta:** The API's `/orderbook` endpoint already does snapshot + delta reconstruction server-side. The SDK leverages this for the initial state, then pages through `/deltas` for subsequent updates. This avoids reimplementing reconstruction logic in the SDK.

4. **Credit cost awareness:** Each `/orderbook` call costs 5 credits, each `/deltas` page costs 2 credits. A 1-hour replay with 10K deltas = 5 + (10 pages * 2) = 25 credits. The SDK should document credit cost per operation.

### Single API Call Data Flow

```
client.get_orderbook("TICKER", timestamp="2026-02-15T12:00:00Z")
    │
    │ Build request payload
    ↓
OrderbookRequest(market_ticker="TICKER", timestamp="2026-02-15T12:00:00Z")
    │
    │ Serialize to dict, send via httpx
    ↓
POST https://api.kalshibook.com/orderbook
Headers: Authorization: Bearer kb-...
Body: {"market_ticker": "TICKER", "timestamp": "2026-02-15T12:00:00Z"}
    │
    │ Check status code
    ↓
├─ 200: Parse JSON → OrderbookResponse dataclass → return
├─ 4xx/5xx: Parse error JSON → raise typed exception
└─ Network error: raise KalshiBookError with connection details
```

## Client Class Design

### Authentication

The existing API uses `Authorization: Bearer kb-...` for data endpoints. The SDK stores the API key and injects it into every request.

```python
class KalshiBook:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.kalshibook.com",
        timeout: float = 30.0,
        sync: bool = False,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        if sync:
            self._http = httpx.Client(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
        else:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
```

**Note:** The existing API uses `Authorization: Bearer kb-...` (verified from `src/api/deps.py` line 53-58). This is standard Bearer token auth, which httpx handles natively.

### Method Naming Convention

Map 1:1 to API endpoints with predictable naming:

| API Endpoint | SDK Method | Returns |
|--------------|------------|---------|
| POST /orderbook | `get_orderbook(ticker, timestamp, depth=None)` | `OrderbookResponse` |
| POST /deltas | `list_deltas(ticker, start_time, end_time, limit=100)` | `AsyncIterator[DeltaRecord]` |
| POST /trades | `list_trades(ticker, start_time, end_time, limit=100)` | `AsyncIterator[TradeRecord]` |
| GET /markets | `list_markets()` | `list[MarketSummary]` |
| GET /markets/{ticker} | `get_market(ticker)` | `MarketDetail` |
| GET /candles/{ticker} | `get_candles(ticker, start_time, end_time, interval="1h")` | `list[CandleRecord]` |
| GET /events | `list_events(category=None, series_ticker=None, status=None)` | `list[EventSummary]` |
| GET /events/{ticker} | `get_event(event_ticker)` | `EventDetail` |
| GET /settlements | `list_settlements(event_ticker=None, result=None)` | `list[SettlementRecord]` |
| GET /settlements/{ticker} | `get_settlement(ticker)` | `SettlementRecord` |

**High-level methods:**

| Method | Purpose | Returns |
|--------|---------|---------|
| `replay_orderbook(ticker, start, end)` | Orderbook state at every delta | `AsyncIterator[tuple[datetime, Orderbook]]` |
| `stream_trades(ticker, start, end)` | All trades in time range | `AsyncIterator[TradeRecord]` (alias for list_trades) |

### Context Manager for Connection Lifecycle

```python
# Async usage
async with KalshiBook(api_key="kb-...") as client:
    orderbook = await client.get_orderbook(...)

# Sync usage
with KalshiBook(api_key="kb-...", sync=True) as client:
    orderbook = client.get_orderbook(...)
```

The context manager ensures the httpx client is properly closed, releasing connection pool resources.

## Models Design

### Use dataclasses, Not Pydantic

**Decision: Use stdlib `dataclasses` for SDK models, not Pydantic.**

Rationale:
- **Minimal dependencies:** The SDK should have exactly one dependency: `httpx`. Adding Pydantic adds 2MB+ to install size and pulls in `annotated-types` and `pydantic-core`.
- **The server uses Pydantic, the SDK doesn't need to:** Pydantic's value is request validation on the server. The SDK receives already-validated JSON from the server -- it just needs to deserialize.
- **Performance:** Dataclass construction is ~10x faster than Pydantic model construction. For replay loops processing thousands of deltas, this matters.
- **Python 3.10+ compatibility:** Dataclasses with `slots=True` and `frozen=True` are efficient and immutable.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class OrderbookLevel:
    price: int      # cents (1-99)
    quantity: int

@dataclass(frozen=True, slots=True)
class OrderbookResponse:
    market_ticker: str
    timestamp: datetime
    snapshot_basis: datetime
    deltas_applied: int
    yes: list[OrderbookLevel]
    no: list[OrderbookLevel]
    request_id: str
    response_time: float

    @classmethod
    def from_dict(cls, data: dict) -> "OrderbookResponse":
        return cls(
            market_ticker=data["market_ticker"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            snapshot_basis=datetime.fromisoformat(data["snapshot_basis"]),
            deltas_applied=data["deltas_applied"],
            yes=[OrderbookLevel(**lv) for lv in data["yes"]],
            no=[OrderbookLevel(**lv) for lv in data["no"]],
            request_id=data["request_id"],
            response_time=data["response_time"],
        )
```

### Mutable Orderbook for Replay

The replay abstraction needs a mutable orderbook that can apply deltas. This is separate from the frozen response dataclass:

```python
@dataclass
class Orderbook:
    """Mutable orderbook state for replay. Not frozen -- mutated by apply_delta."""
    market_ticker: str
    timestamp: datetime
    yes: dict[int, int]  # price_cents -> quantity
    no: dict[int, int]   # price_cents -> quantity

    @classmethod
    def from_response(cls, resp: OrderbookResponse) -> "Orderbook":
        return cls(
            market_ticker=resp.market_ticker,
            timestamp=resp.timestamp,
            yes={lv.price: lv.quantity for lv in resp.yes},
            no={lv.price: lv.quantity for lv in resp.no},
        )

    def apply_delta(self, delta: DeltaRecord) -> None:
        book = self.yes if delta.side == "yes" else self.no
        price = delta.price_cents
        book[price] = book.get(price, 0) + delta.delta_amount
        if book[price] <= 0:
            book.pop(price, None)
        self.timestamp = delta.ts

    def copy(self) -> "Orderbook":
        return Orderbook(
            market_ticker=self.market_ticker,
            timestamp=self.timestamp,
            yes=dict(self.yes),
            no=dict(self.no),
        )

    @property
    def best_yes(self) -> int | None:
        return max(self.yes.keys()) if self.yes else None

    @property
    def best_no(self) -> int | None:
        return max(self.no.keys()) if self.no else None

    @property
    def spread(self) -> int | None:
        by, bn = self.best_yes, self.best_no
        if by is not None and bn is not None:
            return 100 - by - (100 - bn)  # binary market spread
        return None
```

**This mirrors the server's reconstruction logic** (`src/api/services/reconstruction.py` lines 111-123) exactly, ensuring SDK-side and server-side orderbook states are identical.

## Integration Points

### With Existing API

| Integration Point | How SDK Uses It | Notes |
|-------------------|-----------------|-------|
| `POST /orderbook` | `get_orderbook()` + initial state for `replay_orderbook()` | 5 credits per call |
| `POST /deltas` | `list_deltas()` auto-paginator + delta stream for `replay_orderbook()` | 2 credits per page, cursor-based |
| `POST /trades` | `list_trades()` auto-paginator | 2 credits per page, cursor-based |
| `GET /markets` | `list_markets()` | 1 credit, no pagination |
| `GET /markets/{ticker}` | `get_market()` | 1 credit |
| `GET /candles/{ticker}` | `get_candles()` | 3 credits, query params |
| `GET /events` | `list_events()` | 1 credit, query param filters |
| `GET /events/{ticker}` | `get_event()` | 1 credit |
| `GET /settlements` | `list_settlements()` | 1 credit, query param filters |
| `GET /settlements/{ticker}` | `get_settlement()` | 1 credit |
| `GET /health` | `health()` | No auth required |
| OpenAPI spec at `/openapi.json` | Reference for endpoint contracts | Not consumed at runtime |
| Error envelope `{"error": {...}}` | Parsed and mapped to typed exceptions | All error codes mapped |
| Response headers `X-Credits-*` | Exposed as `client.credits_remaining` property | Updated after each request |

### Authentication Integration

The SDK uses the same auth mechanism as the API playground and curl examples:

```
Authorization: Bearer kb-abc123...
```

The SDK does NOT handle user signup, login, or API key creation. Those are dashboard operations. The SDK assumes the user already has an API key.

### Credit Header Tracking

The API returns credit info in response headers. The SDK should expose this:

```python
# After any API call, the client's credit state is updated
orderbook = await client.get_orderbook(...)
print(client.credits_remaining)  # from X-Credits-Remaining header
print(client.credits_used)       # from X-Credits-Used header
print(client.credits_total)      # from X-Credits-Total header
```

### New Components (SDK-Only, No Server Changes)

The SDK is a pure client-side addition. No changes to the existing server code are required.

| Component | New/Modified | Purpose |
|-----------|--------------|---------|
| `sdk/` directory | NEW | Entire SDK package |
| Root `pyproject.toml` | MODIFIED | Add `[tool.uv.workspace]` section |
| `sdk/pyproject.toml` | NEW | SDK package metadata, deps, PyPI config |
| `sdk/src/kalshibook/` | NEW | SDK source code |
| `sdk/tests/` | NEW | SDK tests |
| `sdk/examples/` | NEW | Usage examples |

### What is NOT Modified

- All `src/api/` code remains unchanged
- All `src/collector/` code remains unchanged
- Database schema unchanged
- Dashboard unchanged
- No new API endpoints needed

## Build Order (Dependency-Driven)

```
Step 1: Package Scaffolding
   ├─ Create sdk/ directory with pyproject.toml
   ├─ Add [tool.uv.workspace] to root pyproject.toml
   ├─ Create kalshibook/__init__.py with version
   └─ Verify: `uv sync` resolves workspace, `from kalshibook import __version__` works

   DEPENDENCY: None.

Step 2: Models + Exceptions
   ├─ Define all response dataclasses (mirror API models)
   ├─ Define exception hierarchy (mirror server error codes)
   ├─ Unit tests for from_dict() and exception mapping
   └─ Verify: Models can round-trip from sample API JSON

   DEPENDENCY: Step 1 (package exists).

Step 3: HTTP Transport + Client Core
   ├─ _http.py: httpx wrapper with auth injection, error mapping
   ├─ client.py: KalshiBook class with sync/async support
   ├─ Implement non-paginated methods: get_orderbook, list_markets, get_market, etc.
   ├─ Context manager support (__aenter__/__aexit__)
   └─ Verify: Client can call real API endpoints

   DEPENDENCY: Step 2 (models and exceptions exist).

Step 4: Pagination
   ├─ _pagination.py: async generator for cursor-based endpoints
   ├─ Implement list_deltas, list_trades as auto-paginating methods
   └─ Verify: Can paginate through multi-page delta result sets

   DEPENDENCY: Step 3 (client can make HTTP calls).

Step 5: High-Level Abstractions
   ├─ replay.py: replay_orderbook async generator
   ├─ Orderbook domain model with apply_delta
   ├─ stream_trades convenience method
   └─ Verify: Can replay orderbook for a real market across a time range

   DEPENDENCY: Step 4 (pagination works for /deltas).

Step 6: Polish + Publish
   ├─ Examples directory with working scripts
   ├─ Docstrings on all public methods
   ├─ SDK reference docs (pdoc auto-generation)
   ├─ PyPI publishing setup in pyproject.toml
   └─ Verify: `pip install kalshibook` works from PyPI

   DEPENDENCY: Step 5 (full feature set).
```

## Anti-Patterns

### Anti-Pattern 1: Generating SDK from OpenAPI Spec

**What people do:** Use `openapi-python-client` or `openapi-generator` to auto-generate the SDK from the `/openapi.json` spec.

**Why it's wrong for this project:** Generated code produces a networking layer but cannot generate the high-level abstractions (replay_orderbook, stream_trades) that are the SDK's primary value. The generated pagination handling is generic and doesn't match cursor-based patterns well. Generated code requires post-processing for idiomatic Python. For 10 endpoints, hand-writing is faster than fighting a code generator.

**Do this instead:** Hand-write the SDK with 1:1 endpoint methods. The API is small enough (10 endpoints) that maintenance burden is negligible. Reserve code generation for the future TypeScript SDK (mentioned in PROJECT.md) where the economics are different (fewer TypeScript experts on team).

### Anti-Pattern 2: Importing Server Pydantic Models into SDK

**What people do:** Share Pydantic models between server and SDK (e.g., `from src.api.models import OrderbookResponse`).

**Why it's wrong:** Creates a deployment dependency. Users who `pip install kalshibook` would need the entire server package (FastAPI, asyncpg, structlog, etc.) installed. The SDK must be an independent package with minimal dependencies.

**Do this instead:** Define standalone dataclasses in the SDK that mirror the API's response structure. They're simple enough to keep in sync manually, especially in a monorepo where changes are visible in the same PR.

### Anti-Pattern 3: Loading All Pages Before Returning

**What people do:** `list_deltas()` fetches all pages into a list and returns the complete list.

**Why it's wrong:** A full day of deltas for an active market can be 100K+ records. Loading all into memory before the user sees any data wastes memory and adds latency. Users doing backtest often process records sequentially and don't need them all in memory.

**Do this instead:** Return an async generator that yields individual records. Users who need a list can do `list(await client.list_deltas(...))` explicitly.

### Anti-Pattern 4: Separate Sync and Async Client Classes

**What people do:** Create `KalshiBook` and `AsyncKalshiBook` as two separate classes with duplicated method signatures.

**Why it's wrong:** Method duplication means every API change requires updating two classes. Testing doubles. Documentation doubles.

**Do this instead:** Single `KalshiBook` class with `sync=True` flag that switches the underlying httpx client. Internally, the sync path uses `httpx.Client` and the async path uses `httpx.AsyncClient`. Method signatures stay identical. For pagination, sync mode converts async generators to sync generators internally.

## Scaling Considerations

| Concern | 10 Users | 1K Users | 10K Users |
|---------|----------|----------|-----------|
| SDK package size | N/A (constant) | N/A (constant) | N/A (constant) |
| API request volume | Low, free tier covers | Moderate, PAYG covers | High, may need rate limit handling in SDK |
| Replay memory | ~1MB per active replay | Same (per-user) | Same (per-user) |
| SDK maintenance | 10 endpoints, trivial | Add retry logic, better docs | Consider async connection pooling |

The SDK is client-side software -- it scales with user count on the API, not with SDK complexity. The primary scaling concern is the API server, not the SDK.

## Sources

- [Alpaca-py SDK architecture (GitHub)](https://github.com/alpacahq/alpaca-py) -- HIGH confidence, production SDK for financial data API
- [Polygon.io client-python (GitHub)](https://github.com/polygon-io/client-python) -- HIGH confidence, production SDK with auto-pagination
- [Azure SDK Python Design Guidelines](https://azure.github.io/azure-sdk/python_design.html) -- HIGH confidence, comprehensive SDK design principles
- [uv Workspaces documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/) -- HIGH confidence, official docs
- [LSST vertical monorepo architecture for FastAPI + client](https://sqr-075.lsst.io/) -- MEDIUM confidence, detailed monorepo SDK pattern
- [Stainless: Build vs Buy SDKs](https://www.stainless.com/blog/build-vs-buy-sdks) -- MEDIUM confidence, SDK generation tradeoffs
- [Speakeasy: Python SDK generation comparison](https://www.speakeasy.com/docs/sdks/languages/python/oss-comparison-python) -- MEDIUM confidence, generated vs hand-written analysis
- Existing KalshiBook API source code (`src/api/`) -- HIGH confidence, primary source

---
*Architecture research for: KalshiBook Python SDK*
*Researched: 2026-02-17*
