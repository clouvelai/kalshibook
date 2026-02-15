# Phase 4: Backtesting-Ready API - Research

**Researched:** 2026-02-15
**Domain:** Public trade capture (WS), settlement normalization, OHLC candlestick computation, event/market hierarchy (Series > Event > Market), collector extension, new API endpoints
**Confidence:** HIGH

## Summary

Phase 4 completes the data API layer so customers can build their own backtesting frameworks. Four capability gaps must be filled: (1) capturing public trade executions alongside orderbook data, (2) normalizing settlement/resolution data into queryable format, (3) serving candlestick/OHLC data at multiple intervals, and (4) exposing the Series > Event > Market hierarchy. The work divides naturally into collector-side changes (trade WS subscription, settlement data capture) and API-side changes (new endpoints for trades, settlements, candles, and hierarchy).

The collector already subscribes to `orderbook_delta` and `market_lifecycle_v2` channels. Adding the `trade` channel follows the identical subscription pattern -- same JSON command format (`{"cmd": "subscribe", "params": {"channels": ["trade"]}}`), same message routing in `_handle_message`. Trade messages arrive as `{"type": "trade", "sid": N, "msg": {...}}` with fields: `trade_id`, `market_ticker`, `yes_price`, `no_price`, `count`, `taker_side`, `ts`. This data goes into a new `trades` table partitioned daily (same pattern as `deltas`). The settlement data comes from two sources: (a) the `market_lifecycle_v2` channel already captures `determined`/`settled` events with result data in the metadata JSONB, and (b) the Kalshi REST `GET /markets/{ticker}` endpoint provides `result`, `settlement_value`, `settlement_ts` fields for resolved markets. Both sources feed a `settlements` table with denormalized columns. Candlestick data can be computed from raw trade data using SQL time-bucket aggregation, avoiding the complexity and API rate limits of proxying Kalshi's own candlestick endpoint. Event/market hierarchy requires enriching the existing `markets` table with series data and adding `events` and `series` tables populated from Kalshi REST API on discovery.

**Primary recommendation:** Extend the collector to subscribe to the `trade` WS channel (no market_tickers filter -- receive all trades). Add a `trades` table (daily partitioned), a `settlements` table, an `events` table, and a `series` table. Compute candles from raw trade data using Postgres `date_trunc`/`time_bucket` aggregation in SQL (no Kalshi REST proxy). Enrich market metadata via Kalshi REST `GET /markets/{ticker}` on lifecycle events. Add four new API endpoint groups: `/trades`, `/settlements`, `/candles`, `/events`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Public trade capture
- Add `trades` WS channel subscription to the collector -- capture all public trade executions
- Store trade data: timestamp, price, quantity, side, market ticker
- Serve trade history via API endpoint with time range + market filtering
- This is essential -- backtesters need real execution data, not just simulated fills from orderbook state

#### Settlement data
- Normalize settlement/resolution data into a proper queryable format (not buried in JSONB metadata)
- Reference Kalshi's `/settlements` REST endpoint for data model
- Backtesters need clean resolution data for P&L calculation: market ticker, outcome, settlement time

#### Candlestick/OHLC data
- Serve candlestick data at 1-minute, 1-hour, and 1-day intervals
- Candles include OHLC for bid/ask, trade prices, volume, and open interest
- Enables strategy-level backtesting (directional/momentum) for customers who don't need full L2 orderbook replay

#### Event/market hierarchy
- Expose the Series > Event > Market structure where series exists
- Event > Market relationship for events without a series
- Backtesters often need all markets within an event (e.g., all strike prices for "Bitcoin > $X")

#### Data scope
- Forward data only -- no historical backfill for markets that existed before collection started
- Will start fresh when deploying to production

### Claude's Discretion
- Candle data packaging: whether candles are a separate endpoint tier or bundled with existing data (same credit system)
- Whether to compute candles from raw orderbook/trade data vs. proxy from Kalshi's REST API
- API design patterns for new endpoints (follow Phase 2 conventions)
- Credit costs for new endpoints (trades, settlements, candles)
- Collector implementation details for trades WS subscription

### Deferred Ideas (OUT OF SCOPE)
- **Real-time streaming (live orderbook updates via websocket)** -- Future milestone
- **Agent-first SDK/client library (Tavily-style)** -- Next milestone
- **Historical backfill** -- Future consideration
- **Bulk data access** -- Can revisit
- **Multi-market query optimization** -- Can revisit
- **First-party backtesting framework** -- Next milestone
</user_constraints>

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | >=0.31.0 | PostgreSQL driver | Already used; handles all DB operations including new tables |
| FastAPI | >=0.129.0 | API framework | Already used; new route files follow existing patterns |
| Pydantic | >=2.12.5 | Request/response models | Already used; new models extend existing pattern |
| orjson | >=3.11.7 | JSON serialization | Already used; cursor encoding, fast JSON parsing |
| structlog | >=25.5.0 | Structured logging | Already used; all collector and API logging |
| websockets | >=16.0 | WS client | Already used; collector connection manager |
| httpx | >=0.28.1 | HTTP client | Already used (Supabase auth); will also use for Kalshi REST API calls |

### Supporting (Already Installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyarrow | >=23.0.0 | Parquet archival | Extended to archive trade data alongside deltas |

### New Dependencies

**None required.** All capabilities can be built with the existing dependency set. The Kalshi REST API calls use `httpx` (already installed). SQL time-bucket aggregation for candlesticks uses native Postgres functions. No TimescaleDB extension needed.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQL candlestick computation | Proxy Kalshi REST `/candlesticks` | Kalshi's endpoint requires `series_ticker` (not always known), rate-limited, adds external dependency. Computing from own trade data is self-contained and consistent |
| Enriching markets table from REST | Parse everything from lifecycle WS events | WS lifecycle metadata is incomplete (missing `series_ticker`, `result`, `settlement_value`). REST API provides complete market data. Use both: WS for real-time discovery, REST for enrichment |
| Daily partitioned trades table | Monthly partitioned trades table | Daily matches `deltas` pattern; trades are high-volume like deltas. Consistent partitioning strategy |

## Architecture Patterns

### Recommended New File Structure

```
src/
├── collector/
│   ├── models.py          # ADD: TradeExecution dataclass
│   ├── processor.py       # ADD: handle_trade() method (simple, no sequence tracking needed)
│   ├── writer.py          # ADD: trade_buffer, _flush_trades(), settlement_buffer, _flush_settlements()
│   ├── main.py            # ADD: subscribe to "trade" channel, route "trade" messages
│   ├── enrichment.py      # NEW: Kalshi REST API client for market/event/series metadata
│   └── ...existing...
├── api/
│   ├── routes/
│   │   ├── trades.py      # NEW: POST /trades (paginated trade history)
│   │   ├── settlements.py # NEW: GET /settlements, GET /settlements/{ticker}
│   │   ├── candles.py     # NEW: GET /candles/{ticker}
│   │   ├── events.py      # NEW: GET /events, GET /events/{event_ticker}
│   │   └── ...existing...
│   ├── models.py          # ADD: Trade, Settlement, Candle, Event request/response models
│   ├── services/
│   │   └── candles.py     # NEW: SQL candlestick computation service
│   └── main.py            # ADD: register new routers, new OpenAPI tags
└── ...existing...

supabase/migrations/
├── 20260216000001_create_trades.sql       # Partitioned trades table
├── 20260216000002_create_settlements.sql  # Settlement/resolution data
├── 20260216000003_create_events.sql       # Events table
├── 20260216000004_create_series.sql       # Series table
├── 20260216000005_extend_markets.sql      # Add series_ticker, settlement fields to markets
└── 20260216000006_update_partitions.sql   # Update partition function for trades table
```

### Pattern 1: Trade WS Channel Subscription

**What:** Subscribe to the `trade` channel on the existing WS connection alongside `orderbook_delta` and `market_lifecycle_v2`.

**When to use:** At connection start and on reconnect.

**Key insight:** The `trade` channel does NOT require `market_tickers` -- omitting it receives ALL public trades across all markets. This is simpler than orderbook subscriptions and avoids the 1000 subscription cap issue.

**Kalshi WS trade message format (verified):**
```json
{
  "type": "trade",
  "sid": 11,
  "msg": {
    "trade_id": "d91bc706-ee49-470d-82d8-11418bda6fed",
    "market_ticker": "HIGHNY-22DEC23-B53.5",
    "yes_price": 36,
    "yes_price_dollars": "0.360",
    "no_price": 64,
    "no_price_dollars": "0.640",
    "count": 136,
    "count_fp": "136.00",
    "taker_side": "no",
    "ts": 1669149841
  }
}
```

**Implementation in collector/main.py:**
```python
# In _handle_reconnect():
await self._connection.send_subscribe(["trade"])  # No market_tickers = all trades

# In _handle_message():
elif msg_type == "trade":
    await self._handle_trade(msg)
```

**Data model (collector/models.py):**
```python
@dataclass(frozen=True, slots=True)
class TradeExecution:
    """Parsed trade message from Kalshi WS."""
    trade_id: str
    market_ticker: str
    yes_price: int       # cents
    no_price: int        # cents
    count: int           # contracts traded
    taker_side: str      # "yes" or "no"
    ts: datetime
```

### Pattern 2: Settlement Data Capture (Dual Source)

**What:** Capture settlement/resolution data from two complementary sources.

**Source 1 -- WS lifecycle events (real-time):** The collector already receives `market_lifecycle_v2` events. When `event_type` is `determined` or `settled`, the `msg` metadata includes the resolution outcome. This is already stored in the `markets.metadata` JSONB column -- but buried and not queryable.

**Source 2 -- REST API enrichment (complete data):** Call `GET /markets/{ticker}` after a `determined` lifecycle event to get the complete settlement fields: `result` (enum: 'yes', 'no', 'scalar'), `settlement_value` (cents), `settlement_ts` (timestamp). This is authoritative.

**Strategy:** Use lifecycle events as the trigger, REST API as the data source. When a `determined` event arrives, queue a REST API call to `GET /markets/{ticker}` to fetch `result`, `settlement_value`, `settlement_ts` and write to the `settlements` table.

### Pattern 3: Candlestick Computation from Trade Data

**What:** Compute OHLC candles from the raw `trades` table using SQL time-bucket aggregation.

**Why compute vs proxy:** Computing from own data is self-contained, consistent, avoids Kalshi API rate limits, and doesn't require knowing the `series_ticker` (which Kalshi's candlestick endpoint requires as a path param). The project already has all the source data.

**SQL pattern:**
```sql
SELECT
    date_trunc('hour', ts) AS bucket,
    market_ticker,
    -- Trade price OHLC
    (array_agg(yes_price ORDER BY ts ASC))[1] AS open,
    MAX(yes_price) AS high,
    MIN(yes_price) AS low,
    (array_agg(yes_price ORDER BY ts DESC))[1] AS close,
    -- Volume
    SUM(count) AS volume,
    COUNT(*) AS trade_count
FROM trades
WHERE market_ticker = $1 AND ts >= $2 AND ts < $3
GROUP BY bucket, market_ticker
ORDER BY bucket
```

**Candle intervals:** The three required intervals (1m, 1h, 1d) map to Postgres `date_trunc` with `'minute'`, `'hour'`, and `'day'`. No specialized time-series extension needed.

**Bid/ask OHLC:** Candles also include bid/ask OHLC from the orderbook. This requires querying the most recent snapshot before each candle bucket start to get bid/ask prices. A pragmatic approach: trade price OHLC from `trades` table + separate snapshot-based bid/ask values, OR compute bid/ask from the `deltas` table. Simplest MVP: trade price candles first, then add bid/ask OHLC from the last orderbook state at each interval boundary.

**Recommendation:** Start with trade-price candles (OHLC + volume from `trades` table). This is the most valuable data for backtesting. Bid/ask OHLC and open interest can be added as enrichment in a follow-up or as part of this phase if time permits. Trade-price candles alone satisfy the "directional/momentum strategy" use case described in the context.

### Pattern 4: Event/Market Hierarchy

**What:** Expose the Kalshi Series > Event > Market structure through new tables and API endpoints.

**Current state:** The `markets` table has `event_ticker` (populated from lifecycle events) but no `series_ticker`. There is no `events` or `series` table.

**Data sources:**
- `GET /events?status=open&with_nested_markets=true` -- bulk discovery of events and their markets
- `GET /events/{event_ticker}` -- single event detail
- `GET /series/{series_ticker}` -- series metadata
- `GET /series` -- series listing with category filter
- Lifecycle WS events -- real-time event_ticker from market discovery

**Tables needed:**
```sql
-- Events: real-world occurrences (elections, economic indicators, etc.)
CREATE TABLE events (
    event_ticker TEXT PRIMARY KEY,
    series_ticker TEXT,         -- FK to series (nullable, not all events have series)
    title TEXT,
    sub_title TEXT,
    category TEXT,
    mutually_exclusive BOOLEAN,
    status TEXT,                -- open, closed, settled
    strike_date TIMESTAMPTZ,
    strike_period TEXT,
    metadata JSONB,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Series: recurring event templates (e.g., "Monthly Jobs Report")
CREATE TABLE series (
    ticker TEXT PRIMARY KEY,
    title TEXT,
    frequency TEXT,            -- daily, weekly, monthly
    category TEXT,
    tags TEXT[],
    settlement_sources JSONB,
    metadata JSONB,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Enrichment strategy:** When the collector discovers a new market via lifecycle events, it already has `event_ticker` from the message. Trigger a REST API call to:
1. `GET /events/{event_ticker}` to populate the `events` table and get `series_ticker`
2. `GET /series/{series_ticker}` if series_ticker is new, to populate the `series` table
3. `GET /markets/{ticker}` to enrich the market with `series_ticker`, settlement fields, and complete metadata

This enrichment can be async (fire-and-forget background task) to avoid slowing the main WS message loop.

### Pattern 5: Consistent API Endpoint Design

**What:** All new endpoints follow the Phase 2 conventions established in orderbook.py, deltas.py, markets.py.

**Conventions from existing code:**
- Route files in `src/api/routes/` with dedicated `APIRouter(tags=[...])`
- Request/response models in `src/api/models.py` using Pydantic v2
- Credit gating via `Depends(require_credits(cost))` -- every data endpoint has a credit cost
- Cursor-based pagination for list endpoints (same orjson-encoded base64 pattern)
- Consistent response envelope: `{data: [...], next_cursor, has_more, request_id, response_time}`
- Time measurement with `time.monotonic()` for response_time
- Error handling via `KalshiBookError` subclasses

### Anti-Patterns to Avoid

- **Don't proxy Kalshi's candlestick endpoint for serving candles:** Adds external dependency, rate limit risk, requires series_ticker. Compute from own data.
- **Don't block the WS message loop for REST API calls:** Market enrichment (REST calls to Kalshi) must be async background tasks, not inline.
- **Don't store settlement data only in JSONB metadata:** The whole point is normalization into queryable columns.
- **Don't create separate trade/settlement WS channels or connections:** Use the single existing connection; just add channel subscriptions.
- **Don't forget partition management for the trades table:** Must extend the existing `create_future_partitions()` function to also create daily trade partitions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-bucket aggregation | Custom Python candle builder | Postgres `date_trunc` + aggregate functions | SQL is faster, simpler, handles all interval math; avoids loading raw data into app memory |
| Pagination for trade/settlement endpoints | New cursor encoding scheme | Existing `_encode_cursor`/`_decode_cursor` from deltas.py | Already proven, same composite (ts, id) pattern works for trades |
| REST API client for Kalshi | Raw httpx calls scattered everywhere | Dedicated `enrichment.py` module with typed methods | Centralizes auth, error handling, rate limiting for Kalshi REST calls |
| Partition management for trades | Separate partition function | Extend existing `create_future_partitions()` | One function manages all partitions; consistent with deltas/snapshots |

**Key insight:** This phase adds new data types but follows the exact same architectural patterns established in Phases 1 and 2. The collector pipeline (WS message -> processor -> writer -> DB) and the API pattern (route -> dependency -> service -> DB) are already proven. No new frameworks or paradigms needed.

## Common Pitfalls

### Pitfall 1: Trade Channel Subscription Without Market Tickers

**What goes wrong:** Subscribing to the `trade` channel with specific `market_tickers` means you only get trades for subscribed markets. If a new market appears, you miss its trades until you subscribe.

**Why it happens:** Following the orderbook subscription pattern where market_tickers is required.

**How to avoid:** Subscribe to `trade` channel WITHOUT `market_tickers` parameter. This receives ALL public trades across all markets. Confirmed from Kalshi docs: "Market specification is optional; you can omit it to get notifications for all trades."

**Warning signs:** Missing trade data for recently discovered markets.

### Pitfall 2: Candlestick Endpoint Requires Series Ticker

**What goes wrong:** Kalshi's `GET /series/{series_ticker}/markets/{ticker}/candlesticks` endpoint requires `series_ticker` as a path parameter. Not all markets have an obvious series_ticker, and it's not stored in the current `markets` table.

**Why it happens:** Kalshi organizes candlesticks under the Series > Market hierarchy.

**How to avoid:** Don't proxy Kalshi's candlestick endpoint. Compute candles from the `trades` table using SQL aggregation. This is self-contained and doesn't require series_ticker.

**Warning signs:** 404 errors from Kalshi's candlestick endpoint for markets without a series.

### Pitfall 3: Trade Timestamps in Epoch Seconds

**What goes wrong:** The trade WS message `ts` field is a Unix epoch timestamp in seconds (integer), not ISO 8601 like some other endpoints. Treating it as milliseconds would cause date parsing errors.

**Why it happens:** Inconsistent timestamp formats across Kalshi's API surfaces.

**How to avoid:** The existing `_parse_ts()` helper in `processor.py` already handles both epoch seconds and milliseconds (checks if value > 1e12). Reuse this helper for trade timestamps.

**Warning signs:** Trade timestamps appearing in the year 52000+.

### Pitfall 4: Settlement Data Race Condition

**What goes wrong:** A market lifecycle `determined` event fires, but the REST API `GET /markets/{ticker}` call to fetch `result`/`settlement_value` may not immediately reflect the determination if there's Kalshi API propagation delay.

**Why it happens:** WS events can arrive before REST API state fully converges.

**How to avoid:** Implement retry logic with a short delay (e.g., retry after 5 seconds if `result` is still empty). Alternatively, extract whatever is in the lifecycle event metadata first, then enrich from REST.

**Warning signs:** Settlements table rows with null `result` or `settlement_value`.

### Pitfall 5: Candle Buckets with Zero Trades

**What goes wrong:** Time intervals where no trades occurred produce no rows in the SQL aggregation, creating gaps in the candle series.

**Why it happens:** `GROUP BY date_trunc(...)` only produces rows for buckets that have data.

**How to avoid:** This is expected behavior for financial candle data -- empty buckets mean no trading activity. Document this in the API response. Consumers typically forward-fill the previous close price for empty intervals. Do NOT generate synthetic candle rows -- that would misrepresent the data.

**Warning signs:** Consumers complaining about "missing" candles. Solution: document the behavior clearly.

### Pitfall 6: Blocking WS Loop with REST API Calls

**What goes wrong:** Making synchronous REST API calls (market enrichment) inside the WS message handler blocks the entire message processing pipeline.

**Why it happens:** Enrichment calls to Kalshi REST API take 100-500ms. Processing WS messages must be fast.

**How to avoid:** Use `asyncio.create_task()` for all REST enrichment calls, same fire-and-forget pattern used for PAYG overage reporting and usage logging. Store task references in a set to prevent GC (pattern from 03-review).

**Warning signs:** WS message lag, watchdog timeouts, increased sequence gaps.

## Code Examples

### New Database Tables

**Trades table (daily partitioned, like deltas):**
```sql
CREATE TABLE trades (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    trade_id TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    yes_price INT NOT NULL,
    no_price INT NOT NULL,
    count INT NOT NULL,
    taker_side TEXT NOT NULL CHECK (taker_side IN ('yes', 'no')),
    ts TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ts, id)
) PARTITION BY RANGE (ts);

CREATE INDEX idx_trades_ticker_ts ON trades (market_ticker, ts);
CREATE INDEX idx_trades_trade_id ON trades (trade_id);
```

**Settlements table:**
```sql
CREATE TABLE settlements (
    market_ticker TEXT PRIMARY KEY REFERENCES markets(ticker),
    event_ticker TEXT,
    result TEXT CHECK (result IN ('yes', 'no', 'all_no', 'all_yes')),
    settlement_value INT,              -- cents, for YES side
    determined_at TIMESTAMPTZ,         -- when outcome was determined
    settled_at TIMESTAMPTZ,            -- when positions were settled
    source TEXT DEFAULT 'lifecycle',   -- lifecycle, rest_api, or manual
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_settlements_event ON settlements (event_ticker);
CREATE INDEX idx_settlements_result ON settlements (result);
```

### Candle SQL Aggregation

```python
# Source: adapted from standard Postgres time-bucket pattern
CANDLE_QUERY = """
SELECT
    date_trunc($4, ts AT TIME ZONE 'UTC') AS bucket,
    market_ticker,
    (array_agg(yes_price ORDER BY ts ASC))[1] AS open,
    MAX(yes_price) AS high,
    MIN(yes_price) AS low,
    (array_agg(yes_price ORDER BY ts DESC))[1] AS close,
    SUM(count) AS volume,
    COUNT(*) AS trade_count
FROM trades
WHERE market_ticker = $1
  AND ts >= $2
  AND ts < $3
GROUP BY bucket, market_ticker
ORDER BY bucket ASC
"""
# $4 is 'minute', 'hour', or 'day'
```

### Trade Route Pattern (follows deltas.py convention)

```python
@router.post("/trades", response_model=TradesResponse)
async def get_trades(
    request: Request,
    body: TradesRequest,
    key: dict = Depends(require_credits(2)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Query public trade executions for a market within a time range."""
    t0 = time.monotonic()
    # ... cursor-based pagination, same pattern as deltas.py ...
```

### Collector Trade Subscription

```python
# In CollectorService._handle_reconnect():
async def _handle_reconnect(self) -> None:
    # Subscribe to lifecycle channel (all events)
    await self._connection.send_subscribe(["market_lifecycle_v2"])
    # Subscribe to trade channel (all trades, no market filter)
    await self._connection.send_subscribe(["trade"])
    # Resubscribe to orderbook channels in batches (existing logic)
    tickers = self._discovery.get_resubscribe_list()
    # ... existing batch resubscription ...
```

### REST API Enrichment Module

```python
# src/collector/enrichment.py
class KalshiRestClient:
    """Async client for Kalshi REST API enrichment."""

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self, api_key_id: str, private_key):
        self._api_key_id = api_key_id
        self._private_key = private_key
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0)

    async def get_market(self, ticker: str) -> dict | None:
        """Fetch complete market data including settlement fields."""
        # Uses same RSA-PSS auth as WS but for REST: KALSHI-ACCESS-KEY, SIGNATURE, TIMESTAMP
        headers = generate_rest_auth_headers(...)
        resp = await self._client.get(f"/markets/{ticker}", headers=headers)
        if resp.status_code == 200:
            return resp.json().get("market")
        return None

    async def get_event(self, event_ticker: str) -> dict | None:
        """Fetch event data with nested markets."""
        headers = generate_rest_auth_headers(...)
        resp = await self._client.get(
            f"/events/{event_ticker}",
            params={"with_nested_markets": True},
            headers=headers,
        )
        if resp.status_code == 200:
            return resp.json().get("event")
        return None

    async def get_series(self, series_ticker: str) -> dict | None:
        """Fetch series metadata."""
        headers = generate_rest_auth_headers(...)
        resp = await self._client.get(f"/series/{series_ticker}", headers=headers)
        if resp.status_code == 200:
            return resp.json().get("series")
        return None
```

## Discretionary Recommendations

### Candle Endpoint Packaging

**Recommendation: Same credit system, separate endpoint, 3 credits per request.**

Candles should be a separate endpoint (`GET /candles/{ticker}`) rather than bundled into markets or trades. Reasoning:
- Different use case: candle consumers are directional/momentum backtester, not L2 replay users
- Different query pattern: interval parameter, time range, different response shape
- Credit cost of 3 sits between deltas (2) and orderbook reconstruction (5) -- candle computation involves aggregation but less than full orderbook replay

### Compute Candles from Raw Trade Data (Not Kalshi REST Proxy)

**Recommendation: Compute from own `trades` table.**

Reasons:
1. **Self-contained:** No external API dependency for serving data
2. **No series_ticker required:** Kalshi's candlestick endpoint needs `series_ticker` as a path param, which we don't always have
3. **Consistent:** Candle data reflects exactly the trades we captured, not Kalshi's potentially different aggregation window
4. **No rate limits:** Kalshi REST API has rate limits that would bottleneck our users
5. **Data alignment:** Our candle data covers exactly the same time range as our trade data -- no confusing gaps

### Credit Costs for New Endpoints

**Recommendation:**

| Endpoint | Cost | Rationale |
|----------|------|-----------|
| `POST /trades` | 2 credits | Same as deltas -- paginated raw data query |
| `GET /settlements/{ticker}` | 1 credit | Simple single-row lookup |
| `GET /settlements` | 1 credit | List query, like markets |
| `GET /candles/{ticker}` | 3 credits | Aggregation query, moderate compute |
| `GET /events` | 1 credit | List query |
| `GET /events/{event_ticker}` | 1 credit | Single event with nested markets |

### API Design for New Endpoints

**Recommendation: Follow Phase 2 conventions exactly.**

- `POST /trades` (not GET) for body-based filtering -- same pattern as `/deltas`
- `GET /candles/{ticker}` with query params for interval and time range (simpler than POST for this use case)
- `GET /settlements` and `GET /settlements/{ticker}` -- simple REST resources
- `GET /events` and `GET /events/{event_ticker}` -- hierarchy navigation
- All endpoints return `{data, request_id, response_time}` envelope
- All data endpoints use `require_credits(cost)` dependency

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Settlements only via portfolio endpoint (auth required) | Market `result`/`settlement_value`/`settlement_ts` fields on public GET /markets/{ticker} | 2025-12-25 (Kalshi API changelog) | Settlement data is now available from the public markets endpoint without portfolio auth |
| Integer-only prices | Fixed-point dollar prices (`yes_price_dollars`) alongside cents | 2025 (Kalshi API v2) | Trade messages include both cent and dollar representations |
| `count` as integer | `count_fp` fixed-point string added | 2025 (Kalshi API v2) | Contract counts support 2 decimal places (but currently whole contracts only) |

## Open Questions

1. **Kalshi REST API auth for enrichment calls**
   - What we know: WS uses RSA-PSS in headers during handshake. REST API uses the same key format but in per-request headers.
   - What's unclear: The exact REST API signature format. The WS auth helper `generate_auth_headers` signs `timestamp + "GET" + ws_path`. REST likely signs `timestamp + method + path`.
   - Recommendation: Check Kalshi docs for REST API auth signature format. The existing `connection.py` auth helpers may need adaptation (sign `timestamp + HTTP_METHOD + request_path` for REST). LOW risk -- well-documented in Kalshi docs.

2. **Open interest data for candles**
   - What we know: Candle spec calls for "open interest" alongside OHLC. Open interest means total outstanding contracts.
   - What's unclear: Open interest is not in the `trades` table -- it's a market-level statistic that requires tracking position creation/closure.
   - Recommendation: Start with trade-price OHLC + volume. Open interest can be sourced from the `ticker` WS channel (provides `open_interest_fp`) or periodic REST API polling. Mark as optional for MVP.

3. **Bid/ask OHLC for candles**
   - What we know: Context asks for "OHLC for bid/ask, trade prices." Bid/ask comes from the orderbook, not trades.
   - What's unclear: Computing bid/ask at each candle interval boundary requires orderbook reconstruction at those timestamps -- potentially expensive.
   - Recommendation: Implement trade-price candles first (from `trades` table). For bid/ask OHLC, sample the top-of-book at each interval boundary using a lighter query against `snapshots` + `deltas`. This can be a separate enrichment step. Document that bid/ask OHLC may not be available for MVP if complexity is high.

## Sources

### Primary (HIGH confidence)
- Kalshi API Docs -- Public Trades WS Channel: https://docs.kalshi.com/websockets/public-trades (trade message format, subscription model)
- Kalshi API Docs -- Get Market: https://docs.kalshi.com/api-reference/market/get-market (settlement fields: result, settlement_value, settlement_ts)
- Kalshi API Docs -- Get Market Candlesticks: https://docs.kalshi.com/api-reference/market/get-market-candlesticks (intervals: 1, 60, 1440 minutes; OHLC schema)
- Kalshi API Docs -- Get Events: https://docs.kalshi.com/api-reference/events/get-events (event schema, series_ticker, with_nested_markets)
- Kalshi API Docs -- Get Event: https://docs.kalshi.com/api-reference/events/get-event (single event detail)
- Kalshi API Docs -- Get Series: https://docs.kalshi.com/api-reference/market/get-series (series schema, settlement_sources)
- Kalshi API Docs -- Get Series List: https://docs.kalshi.com/api-reference/market/get-series-list (series listing)
- Kalshi API Docs -- Get Trades REST: https://docs.kalshi.com/api-reference/market/get-trades (REST trade fields, pagination)
- Kalshi API Docs -- llms.txt index: https://docs.kalshi.com/llms.txt (complete API surface listing)
- Kalshi API Docs -- WebSocket Quick Start: https://docs.kalshi.com/getting_started/quick_start_websockets (subscribe command format, channel names)
- Existing codebase: `src/collector/connection.py`, `processor.py`, `writer.py`, `main.py` (collector architecture)
- Existing codebase: `src/api/routes/deltas.py`, `orderbook.py`, `markets.py` (API conventions)
- Existing codebase: `src/api/deps.py` (credit gating, auth patterns)
- Existing codebase: `supabase/migrations/` (table schemas, partition patterns)

### Secondary (MEDIUM confidence)
- Kalshi API Changelog: https://docs.kalshi.com/changelog (settlement_ts addition date: 2025-12-25)
- Kalshi trade message schema from WebSearch results (trade_id, yes_price, no_price, count, taker_side, ts fields confirmed)

### Tertiary (LOW confidence)
- Open interest availability in `ticker` WS channel -- mentioned in Kalshi docs llms.txt index ("price, volume, and open interest updates") but exact field names not verified from the channel docs directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing libraries sufficient
- Architecture: HIGH -- extends proven patterns from Phases 1-2, verified Kalshi API schemas
- Pitfalls: HIGH -- identified from actual codebase analysis and Kalshi API documentation
- Candle computation approach: MEDIUM -- SQL aggregation pattern is standard but bid/ask OHLC complexity is uncertain
- REST API enrichment auth: MEDIUM -- same key format as WS but REST signature format needs verification

**Research date:** 2026-02-15
**Valid until:** 2026-03-15 (Kalshi API is stable; no major changes expected)
