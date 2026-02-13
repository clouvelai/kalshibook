# Architecture Research

**Domain:** Market data collection + serving (L2 orderbook, prediction markets)
**Researched:** 2026-02-13
**Confidence:** HIGH (verified against Kalshi API docs, Supabase docs, production orderbook system patterns)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER (Railway)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐     │
│  │ WS Connector │  │  Orderbook   │  │   Market Discovery    │     │
│  │ (Kalshi API) │→ │  Processor   │  │ (lifecycle channel)   │     │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘     │
│         │                 │                       │                 │
│  ┌──────┴─────────────────┴───────────────────────┴──────────┐     │
│  │                    Write Buffer / Batcher                  │     │
│  └────────────────────────────┬──────────────────────────────┘     │
├───────────────────────────────┼──────────────────────────────────────┤
│                               ↓                                     │
│                     STORAGE LAYER (Supabase)                        │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐      │
│  │  Snapshots     │  │    Deltas      │  │    Markets       │      │
│  │  (partitioned) │  │  (partitioned) │  │   (metadata)     │      │
│  └────────────────┘  └────────────────┘  └──────────────────┘      │
│                               │                                     │
├───────────────────────────────┼──────────────────────────────────────┤
│                               ↓                                     │
│                     SERVING LAYER (Railway or Supabase)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │  REST API     │  │  WS Stream   │  │  PostgREST (raw)    │      │
│  │  (FastAPI)    │  │  (FastAPI)   │  │  (Supabase auto)    │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
│                               │                                     │
├───────────────────────────────┼──────────────────────────────────────┤
│                               ↓                                     │
│                     AUTH + BILLING LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │ Supabase Auth │  │  API Keys   │  │  Stripe Billing      │      │
│  │  (JWT/RLS)    │  │  (custom)   │  │  (subscriptions)     │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| WS Connector | Authenticate to Kalshi, maintain persistent websocket, handle reconnection with exponential backoff | Python `websockets` library + asyncio, RSA-PSS auth headers |
| Orderbook Processor | Parse snapshot/delta messages, validate sequence numbers, detect gaps, maintain in-memory state for integrity checks | Pure Python, dataclass-based orderbook model |
| Market Discovery | Subscribe to `market_lifecycle_v2` channel, detect new markets, trigger orderbook subscriptions | Runs on same WS connection, no ticker filter needed |
| Write Buffer | Batch incoming deltas, flush to Supabase on interval or batch-size threshold | asyncio queue, 500-1000 row batches, ~1-5 second flush |
| Snapshots Table | Store complete orderbook state at subscription time and periodic intervals | PostgreSQL with range partitioning by timestamp |
| Deltas Table | Store every individual orderbook delta with sequence numbers | PostgreSQL with range partitioning by timestamp, high write volume |
| Markets Table | Market metadata: ticker, title, event, status, settlement info | Standard PostgreSQL table, updated from lifecycle events |
| REST API | Serve reconstructed orderbook state at any timestamp, paginated delta queries | FastAPI with Pydantic models, query Supabase via service role |
| WS Stream | Stream real-time orderbook updates to subscribed clients | FastAPI WebSocket endpoints, fan-out from internal state |
| PostgREST | Auto-generated REST API for raw table access (advanced users) | Supabase built-in, RLS policies for access control |
| API Keys | Per-customer API keys with tier-based rate limits | Custom table in Supabase, middleware validation |
| Stripe Billing | Subscription management, usage tracking, plan enforcement | Stripe SDK, webhook handlers |

## Recommended Project Structure

```
src/
├── collector/              # Ingestion layer (runs on Railway as persistent service)
│   ├── __init__.py
│   ├── main.py             # Entry point, orchestrates connection + processing
│   ├── connection.py       # WS connection management, auth, reconnection
│   ├── processor.py        # Snapshot/delta parsing, sequence validation
│   ├── discovery.py        # Market lifecycle monitoring, subscription management
│   ├── writer.py           # Batched writes to Supabase
│   └── models.py           # Internal data models (OrderbookSnapshot, Delta, etc.)
├── api/                    # Serving layer (runs on Railway or serverless)
│   ├── __init__.py
│   ├── main.py             # FastAPI app entry point
│   ├── routes/
│   │   ├── orderbook.py    # GET /orderbook/{ticker}?at=timestamp
│   │   ├── deltas.py       # GET /deltas/{ticker}?from=&to=
│   │   ├── markets.py      # GET /markets, GET /markets/{ticker}
│   │   └── stream.py       # WS /stream/{ticker} (real-time)
│   ├── middleware/
│   │   ├── auth.py         # API key validation + rate limiting
│   │   └── usage.py        # Usage tracking for billing
│   ├── services/
│   │   ├── reconstruction.py  # Point-in-time orderbook reconstruction
│   │   └── supabase.py     # Supabase client wrapper
│   └── models.py           # API response models (Pydantic)
├── shared/                 # Code shared between collector and API
│   ├── __init__.py
│   ├── config.py           # Environment config, Supabase connection
│   ├── orderbook.py        # Orderbook data structures + reconstruction logic
│   └── kalshi_types.py     # Kalshi message type definitions
├── migrations/             # Supabase SQL migrations
│   ├── 001_markets.sql
│   ├── 002_snapshots.sql
│   ├── 003_deltas.sql
│   ├── 004_api_keys.sql
│   └── 005_rls_policies.sql
└── tests/
    ├── collector/
    ├── api/
    └── shared/
```

### Structure Rationale

- **collector/:** Separate deployable unit. Runs as a long-lived process on Railway. Has no HTTP concerns. Owns the write path.
- **api/:** Separate deployable unit. Runs as a web service. Owns the read path. Can scale independently of collector.
- **shared/:** Prevents duplication of orderbook reconstruction logic and Kalshi type definitions between collector and API.
- **migrations/:** SQL files that define the Supabase schema. Managed via `supabase db push` or Supabase migrations system.

## Architectural Patterns

### Pattern 1: Snapshot + Delta Event Sourcing

**What:** Store raw snapshots and deltas as immutable events. Reconstruct orderbook state at any point in time by replaying deltas forward from the nearest prior snapshot.

**When to use:** Always. This is the core data model. Kalshi's API provides exactly this: an initial `orderbook_snapshot` on subscribe, followed by `orderbook_delta` messages. Store both verbatim.

**Trade-offs:**
- Pro: Complete audit trail. Can reconstruct any historical state. Matches source data model exactly.
- Pro: Write path is simple (append-only).
- Con: Read path requires reconstruction (snapshot + replay deltas). Mitigated by periodic snapshots.
- Con: Storage grows linearly with market activity. Mitigated by partitioning + compression.

**Example:**
```python
# Reconstruction: find nearest snapshot, apply deltas
async def reconstruct_orderbook(ticker: str, at: datetime) -> Orderbook:
    # 1. Find the most recent snapshot before 'at'
    snapshot = await db.snapshots.select("*").eq(
        "market_ticker", ticker
    ).lte("captured_at", at.isoformat()).order(
        "captured_at", desc=True
    ).limit(1).execute()

    # 2. Get all deltas between snapshot and target time
    deltas = await db.deltas.select("*").eq(
        "market_ticker", ticker
    ).gt("ts", snapshot.captured_at.isoformat()).lte(
        "ts", at.isoformat()
    ).order("seq", asc=True).execute()

    # 3. Apply deltas to snapshot
    book = Orderbook.from_snapshot(snapshot)
    for delta in deltas:
        book.apply_delta(delta)
    return book
```

### Pattern 2: Periodic Snapshot Materialization

**What:** Every N minutes (e.g., 5 min), capture and store a full snapshot of each active orderbook's state. This bounds the number of deltas that must be replayed for any reconstruction query.

**When to use:** Once delta volume makes reconstruction slow (likely from the start -- a market may generate hundreds of deltas per minute during active trading).

**Trade-offs:**
- Pro: Bounds reconstruction time to max N minutes of delta replay.
- Pro: Snapshots are self-contained -- useful for quick "what did the book look like at this time?" queries.
- Con: Additional storage. Mitigated by choosing interval based on activity level.
- Con: Snapshot must be taken from known-good in-memory state (the collector already maintains this).

### Pattern 3: Batched Write Pipeline

**What:** Buffer incoming deltas in-memory and flush to Supabase in batches (500-1000 rows per insert) on a timer (1-5 seconds) or when the buffer reaches a size threshold.

**When to use:** Always. Individual row inserts via the Supabase REST API are too slow for high-frequency delta streams. Batch inserts provide 10-100x throughput improvement.

**Trade-offs:**
- Pro: Dramatically reduces database round-trips and connection overhead.
- Pro: Amortizes network latency across many rows.
- Con: Up to N seconds of data loss on crash. Acceptable for MVP (data can be re-collected from the next snapshot).
- Con: Adds buffering complexity.

**Example:**
```python
class WriteBuffer:
    def __init__(self, supabase, flush_interval=2.0, max_batch=500):
        self.buffer: list[dict] = []
        self.supabase = supabase
        self.flush_interval = flush_interval
        self.max_batch = max_batch

    async def add(self, row: dict):
        self.buffer.append(row)
        if len(self.buffer) >= self.max_batch:
            await self.flush()

    async def flush(self):
        if not self.buffer:
            return
        batch, self.buffer = self.buffer[:self.max_batch], self.buffer[self.max_batch:]
        await self.supabase.table("deltas").insert(batch).execute()

    async def run_timer(self):
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
```

## Data Flow

### Ingestion Flow (Kalshi WS -> Supabase)

```
Kalshi WS API (wss://api.elections.kalshi.com/trade-api/ws/v2)
    │
    │ RSA-PSS auth headers on handshake
    │
    ├─ Subscribe: {"cmd": "subscribe", "params": {"channels": ["orderbook_delta"],
    │              "market_tickers": ["TICKER1", "TICKER2", ...]}}
    │
    ├─ Subscribe: {"cmd": "subscribe", "params": {"channels": ["market_lifecycle_v2"]}}
    │  (no ticker filter -- receives ALL market lifecycle events)
    │
    ↓
[WS Connector] ─── raw JSON messages ───→ [Orderbook Processor]
    │                                           │
    │ heartbeat/ping-pong                       ├─ orderbook_snapshot → validate → buffer
    │ reconnect on drop                         ├─ orderbook_delta → validate seq → buffer
    │ re-auth every 30 min                      └─ market_lifecycle → update markets table
    │                                                    │
    ↓                                                    ↓
[Reconnection Manager]                          [Write Buffer]
    │                                                    │
    │ exponential backoff                                │ batch: 500-1000 rows
    │ 1s, 2s, 4s... + jitter                            │ flush: every 2-5 seconds
    │ re-subscribe all tickers                           │
    │ request fresh snapshots                            ↓
    │                                           [Supabase PostgreSQL]
    ↓                                               ├─ snapshots table
[Sequence Gap Detector]                             ├─ deltas table
    │                                               └─ markets table
    │ if seq gap detected:
    │   1. log warning
    │   2. re-subscribe market (triggers fresh snapshot)
    │   3. mark gap in metadata
```

### Serving Flow (Customer API)

```
Customer Request (REST or WebSocket)
    │
    │ API Key in header: X-API-Key: kbook_live_abc123...
    │
    ↓
[API Key Middleware]
    │
    ├─ Validate key exists + is active
    ├─ Check rate limit (tier-based)
    ├─ Track usage for billing
    │
    ↓
[FastAPI Router]
    │
    ├─ GET /v1/orderbook/{ticker}?at={timestamp}
    │       ↓
    │   [Reconstruction Service]
    │       ├─ Find nearest snapshot ≤ timestamp
    │       ├─ Fetch deltas between snapshot and timestamp
    │       ├─ Apply deltas to build point-in-time state
    │       └─ Return full orderbook (bids + asks with quantities)
    │
    ├─ GET /v1/deltas/{ticker}?from={ts}&to={ts}&limit=1000
    │       ↓
    │   [Direct query] → Supabase deltas table (paginated)
    │
    ├─ GET /v1/markets
    │       ↓
    │   [Direct query] → Supabase markets table
    │
    └─ WS /v1/stream/{ticker}
            ↓
        [Stream Manager]
            ├─ Authenticate on handshake
            ├─ Subscribe to Supabase Realtime (deltas table changes)
            │   OR fan-out from collector's internal state
            └─ Push delta JSON to client on each update
```

### Key Data Flows

1. **Snapshot ingestion:** Kalshi WS → `orderbook_snapshot` message → parse all yes/no levels → store as single row in `snapshots` table with JSONB levels + metadata.
2. **Delta ingestion:** Kalshi WS → `orderbook_delta` message → validate `seq` is `prev_seq + 1` → buffer → batch insert into `deltas` table.
3. **Market discovery:** Kalshi WS → `market_lifecycle_v2` → detect `"created"` event → upsert `markets` table → subscribe to `orderbook_delta` for new ticker.
4. **Point-in-time reconstruction:** API request → find nearest snapshot → query deltas in sequence range → apply deltas → return reconstructed book.
5. **Real-time streaming:** Supabase Realtime listens to `deltas` inserts → pushes to connected clients via WebSocket (or: API server subscribes to Supabase Realtime internally, fans out to customer WS connections).

## Supabase Schema Design

### Critical Decision: TimescaleDB is NOT Available

**Finding (HIGH confidence):** TimescaleDB is deprecated on Supabase for PostgreSQL 17 projects. The project's `supabase/config.toml` uses `major_version = 17`. TimescaleDB will NOT be available. Use native PostgreSQL range partitioning instead.

Source: [Supabase TimescaleDB docs](https://supabase.com/docs/guides/database/extensions/timescaledb) -- "deprecated for Postgres 17 projects."

### Recommended Schema

```sql
-- Markets metadata (low volume, simple table)
CREATE TABLE markets (
    ticker TEXT PRIMARY KEY,
    market_id UUID NOT NULL,
    title TEXT,
    event_ticker TEXT,
    status TEXT NOT NULL DEFAULT 'active',  -- active, closed, settled
    category TEXT,
    rules TEXT,
    strike_price NUMERIC,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB  -- flexible field for settlement info, etc.
);

CREATE INDEX idx_markets_status ON markets (status);
CREATE INDEX idx_markets_event ON markets (event_ticker);

-- Orderbook snapshots (moderate volume, partitioned by month)
CREATE TABLE snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    market_ticker TEXT NOT NULL REFERENCES markets(ticker),
    captured_at TIMESTAMPTZ NOT NULL,
    seq BIGINT NOT NULL,           -- WS sequence number at snapshot time
    yes_levels JSONB NOT NULL,     -- [[price_cents, quantity], ...]
    no_levels JSONB NOT NULL,      -- [[price_cents, quantity], ...]
    source TEXT NOT NULL DEFAULT 'ws_subscribe',  -- ws_subscribe | periodic | resubscribe
    PRIMARY KEY (captured_at, id)
) PARTITION BY RANGE (captured_at);

-- Create initial partitions (automate with pg_cron or application logic)
CREATE TABLE snapshots_2026_02 PARTITION OF snapshots
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE snapshots_2026_03 PARTITION OF snapshots
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

CREATE INDEX idx_snapshots_ticker_time ON snapshots (market_ticker, captured_at DESC);

-- Orderbook deltas (HIGH volume, partitioned by day)
CREATE TABLE deltas (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    market_ticker TEXT NOT NULL,   -- no FK for write performance
    ts TIMESTAMPTZ NOT NULL,       -- delta timestamp from Kalshi
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    seq BIGINT NOT NULL,           -- WS sequence number
    sid BIGINT NOT NULL,           -- WS subscription ID
    price_cents INT NOT NULL,      -- price in cents (1-99)
    delta_amount INT NOT NULL,     -- signed quantity change
    side TEXT NOT NULL,            -- 'yes' or 'no'
    PRIMARY KEY (ts, id)
) PARTITION BY RANGE (ts);

-- Create daily partitions (automate via pg_cron or application)
CREATE TABLE deltas_2026_02_13 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-13') TO ('2026-02-14');
CREATE TABLE deltas_2026_02_14 PARTITION OF deltas
    FOR VALUES FROM ('2026-02-14') TO ('2026-02-15');
-- ... etc

CREATE INDEX idx_deltas_ticker_seq ON deltas (market_ticker, seq);
CREATE INDEX idx_deltas_ticker_ts ON deltas (market_ticker, ts);

-- API keys (low volume)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    key_hash TEXT NOT NULL UNIQUE,      -- hashed API key (never store plaintext)
    key_prefix TEXT NOT NULL,           -- first 8 chars for identification (kbook_live_)
    name TEXT,
    tier TEXT NOT NULL DEFAULT 'free',  -- free, pay_as_you_go, project, enterprise
    rate_limit_per_min INT NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    metadata JSONB
);

CREATE INDEX idx_api_keys_hash ON api_keys (key_hash) WHERE is_active = true;
CREATE INDEX idx_api_keys_user ON api_keys (user_id);

-- Usage tracking (for billing, moderate volume)
CREATE TABLE usage_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    endpoint TEXT NOT NULL,
    called_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    response_ms INT,
    PRIMARY KEY (called_at, id)
) PARTITION BY RANGE (called_at);
```

### Schema Design Rationale

**Why JSONB for snapshot levels:** A snapshot's yes/no levels are a variable-length array of `[price, quantity]` pairs. Normalizing into rows would explode row count (20-50 levels per side per snapshot). JSONB keeps the snapshot as a single atomic row, which is fast to write and fast to read as a unit. We never need to query *individual* levels within a snapshot -- we always read the whole thing and process in application code.

**Why normalized columns for deltas (not JSONB):** Deltas are individual events with fixed fields. They benefit from PostgreSQL indexing on `market_ticker`, `ts`, and `seq`. Each delta is small (one price level change). Normalized columns enable efficient range queries without JSONB extraction overhead.

**Why daily partitions for deltas:** Active markets can generate thousands of deltas per day across all markets. Daily partitions keep each chunk small, enable efficient time-range queries (PostgreSQL prunes irrelevant partitions), and allow simple data lifecycle management (drop old partitions for archiving).

**Why monthly partitions for snapshots:** Snapshots are less frequent (one per market per subscription + periodic). Monthly granularity is sufficient.

**Why no foreign key on deltas.market_ticker:** FK constraints add overhead to every insert. Since deltas are the highest-volume table and market_ticker values are validated at the application layer (we only receive deltas for markets we subscribed to), skipping the FK is a deliberate write-performance optimization.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| MVP (10 markets, <10 customers) | Single WS connection, single Railway collector process, Supabase Free/Pro plan, PostgREST for raw access. Partition management manual or pg_cron. |
| Growth (100 markets, 100 customers) | Still single WS connection (within 1K limit). Add periodic snapshot materialization. Monitor Supabase write throughput. Add Redis for API rate limiting if needed. |
| Scale (500+ markets, 1K+ customers) | Multiple WS connections (connection pooling). Dedicated collector per connection. Consider moving deltas writes to direct PostgreSQL connection (bypass PostgREST). Supabase Pro with higher Realtime limits. |
| Full coverage (5K+ markets) | 5+ WS connections. Need consensus/dedup layer if redundant collectors. Consider moving time-series storage to dedicated TSDB (QuestDB, ClickHouse) while keeping Supabase for auth/API keys/metadata. |

### Scaling Priorities

1. **First bottleneck: Supabase write throughput for deltas.** At ~100 active markets with moderate activity, you might see 50-200 deltas/second. Batched inserts of 500 rows handle this easily. Monitor and increase batch size or add direct PG connection if needed.
2. **Second bottleneck: Reconstruction query time.** As delta history grows, reconstruction requires scanning more rows. Periodic snapshots (every 5 min) bound this. Add materialized views for "latest orderbook" if live queries become slow.
3. **Third bottleneck: Supabase Realtime limits.** Free plan allows 200 concurrent connections and 100 messages/second. If streaming to many customers, hit this fast. Move to custom WebSocket fan-out from the API server instead of relying on Supabase Realtime for customer-facing streaming.

## Anti-Patterns

### Anti-Pattern 1: Storing Full Orderbook State on Every Delta

**What people do:** On each delta, reconstruct the full orderbook and store the complete state.
**Why it's wrong:** Explodes storage by orders of magnitude. A delta is ~100 bytes; a full orderbook is ~2-5 KB. With 100 deltas/second across all markets, this becomes 200-500 KB/s of redundant data. Reconstruction on read is dramatically cheaper than materialization on every write.
**Do this instead:** Store raw deltas. Periodically materialize snapshots (every 5 min). Reconstruct on demand for point-in-time queries.

### Anti-Pattern 2: Using Supabase Realtime as the Primary Streaming Mechanism to Customers

**What people do:** Have customers subscribe directly to Supabase Realtime database change events on the deltas table.
**Why it's wrong:** Supabase Realtime checks RLS policies for every message for every subscriber. 100 subscribers + 1 insert = 100 policy checks. This creates a database bottleneck. Free plan limits are 200 connections and 100 msg/sec -- easily exceeded. Also, Supabase Realtime does NOT guarantee delivery.
**Do this instead:** Build a custom WebSocket fan-out in the API server. The collector pushes updates to the API server (or the API server reads from Supabase Realtime as a single subscriber), then the API server fans out to customer connections. This decouples customer count from database load.

### Anti-Pattern 3: Individual Row Inserts for Deltas

**What people do:** Insert each delta individually as it arrives from the WebSocket.
**Why it's wrong:** Each insert is an HTTP round-trip through PostgREST. At 50-200 deltas/second, this means 50-200 HTTP requests/second. Latency adds up, and you hit Supabase API rate limits.
**Do this instead:** Buffer deltas in memory, flush in batches of 500-1000 rows every 2-5 seconds.

### Anti-Pattern 4: Relying on Application-Level Sequence Tracking Without Gap Detection

**What people do:** Assume every delta arrives in order and none are missed.
**Why it's wrong:** WebSocket connections drop. Messages can be lost. Network interruptions happen. Without sequence gap detection, the stored delta stream becomes corrupt and reconstructions produce incorrect orderbook states.
**Do this instead:** Track `seq` per market per subscription (`sid`). On gap detection, immediately re-subscribe to the market (which triggers a fresh snapshot), log the gap, and mark affected time ranges. The fresh snapshot provides a new known-good starting point.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Kalshi WebSocket API | Persistent WS connection, RSA-PSS auth headers, re-auth every 30 min | Endpoint: `wss://api.elections.kalshi.com/trade-api/ws/v2`. Auth requires `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-SIGNATURE` (RSA-PSS SHA-256), `KALSHI-ACCESS-TIMESTAMP`. |
| Supabase PostgreSQL | `supabase-py` client with service role key for writes, anon key for reads via PostgREST | Batch inserts for deltas. Direct SQL for complex reconstruction queries. |
| Supabase Auth | JWT-based auth for dashboard users, API key auth for programmatic access | Dashboard users get JWT via Supabase Auth. API customers use custom API keys validated in middleware. |
| Supabase Realtime | Internal subscription only (API server subscribes as single client) | Do NOT expose directly to customers. Use as internal transport from DB to API server. |
| Stripe | Webhook handler for subscription events, SDK for customer portal | Store Stripe customer ID in Supabase user profile. Track usage for metered billing. |
| Railway | Persistent service for collector, web service for API | Collector needs always-on process. API can scale horizontally. Separate Railway services. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Collector -> Supabase | HTTP (PostgREST batched inserts) or direct PG connection | Service role key. No RLS bypass needed (service role already bypasses). |
| API Server -> Supabase | HTTP (PostgREST reads) or direct PG for reconstruction | Anon key + RLS for customer-scoped data. Service role for admin operations. |
| Collector -> API Server | No direct communication needed for MVP | In future: could push real-time updates via Redis pub/sub or shared Supabase Realtime channel to avoid API server polling. |
| Customer -> API Server | HTTPS REST + WSS WebSocket | API key in header. TLS required in production. |
| Dashboard -> Supabase | Direct Supabase client (JS SDK) | JWT auth. RLS policies scope data to user's API keys and usage. |

## Build Order (Dependencies)

Build order is driven by data flow dependencies: you can't serve data you haven't collected, and you can't collect data you have nowhere to store.

```
Phase 1: Schema + Collector Core
   ├─ Supabase schema (migrations for markets, snapshots, deltas)
   ├─ WS connection management (auth, reconnect, heartbeat)
   ├─ Snapshot/delta parsing and validation
   ├─ Batched write pipeline
   └─ Market discovery (lifecycle channel)

   WHY FIRST: Everything else depends on having data flowing into the database.
   DEPENDENCY: None (Supabase project already initialized).

Phase 2: API Foundation
   ├─ FastAPI app skeleton
   ├─ API key table + middleware
   ├─ Orderbook reconstruction service
   ├─ Basic REST endpoints (GET /orderbook, /deltas, /markets)
   └─ Pydantic response models

   WHY SECOND: Requires data in the database (Phase 1).
   DEPENDENCY: Phase 1 complete, data flowing.

Phase 3: Real-Time Streaming
   ├─ WebSocket streaming endpoint
   ├─ Fan-out architecture (subscribe to Supabase Realtime internally)
   ├─ Client subscription management
   └─ Backpressure handling

   WHY THIRD: Requires both collector (data source) and API foundation (auth/routing).
   DEPENDENCY: Phase 1 + Phase 2.

Phase 4: Auth + Billing
   ├─ Supabase Auth integration (dashboard users)
   ├─ Stripe subscription setup
   ├─ Tier-based rate limiting
   ├─ Usage tracking and metered billing
   └─ Customer dashboard (API key management, usage)

   WHY FOURTH: Can ship with simple API keys before monetization.
   DEPENDENCY: Phase 2 (API key infrastructure exists).

Phase 5: Hardening + Scale
   ├─ Partition management automation (pg_cron or application)
   ├─ Data retention policies
   ├─ Monitoring and alerting (gap detection, write latency)
   ├─ Connection pooling (multiple WS connections)
   └─ Performance optimization (materialized views, caching)

   WHY FIFTH: Operational maturity after core product works.
   DEPENDENCY: All prior phases.
```

## Serving Layer Decision: FastAPI Custom vs PostgREST

**Recommendation: Use FastAPI as the primary serving layer. Expose PostgREST as a secondary "raw data" endpoint for advanced users.**

| Criterion | PostgREST (Supabase auto) | FastAPI (Custom) |
|-----------|--------------------------|------------------|
| Orderbook reconstruction | Cannot do (requires application logic) | Full control over snapshot+delta replay |
| WebSocket streaming | Not supported (PostgREST is REST-only) | Native FastAPI WebSocket support |
| Rate limiting by API key | Requires RLS + custom functions (clunky) | Clean middleware pattern |
| Response shaping | Limited to table schema + views | Full Pydantic model control |
| Agent-friendly docs | Auto-generated but not domain-specific | Custom OpenAPI with domain-specific docs |
| Setup effort | Zero (already exists) | Moderate (standard FastAPI patterns) |
| Raw data access | Excellent (direct table queries) | Would need to reimplement pagination/filtering |

**Hybrid approach:** PostgREST handles "give me raw deltas for ticker X between time A and B" (it's great at this). FastAPI handles "give me the reconstructed orderbook at time T" and WebSocket streaming (PostgREST cannot do these).

## Sources

- [Kalshi Orderbook Updates WebSocket docs](https://docs.kalshi.com/websockets/orderbook-updates) -- HIGH confidence, official
- [Kalshi WebSocket Connection docs](https://docs.kalshi.com/websockets/websocket-connection) -- HIGH confidence, official
- [Kalshi WebSocket Quick Start](https://docs.kalshi.com/getting_started/quick_start_websockets) -- HIGH confidence, official
- [Kalshi Market Lifecycle Channel](https://docs.kalshi.com/websockets/market-&-event-lifecycle) -- HIGH confidence, official
- [Supabase TimescaleDB deprecation on PG17](https://supabase.com/docs/guides/database/extensions/timescaledb) -- HIGH confidence, official
- [Supabase Realtime Limits](https://supabase.com/docs/guides/realtime/limits) -- HIGH confidence, official
- [Supabase Table Partitioning](https://supabase.com/docs/guides/database/partitions) -- HIGH confidence, official
- [Supabase REST API / PostgREST docs](https://supabase.com/docs/guides/api) -- HIGH confidence, official
- [QuestDB L2 Orderbook Array Schema](https://questdb.com/blog/level-2-order-book-data-into-questdb-arrays/) -- MEDIUM confidence, third-party reference for schema patterns
- [Gradient Trader: Efficient Orderbook Storage](https://rickyhan.com/jekyll/update/2017/10/28/how-to-handle-order-book-data.html) -- MEDIUM confidence, well-known reference for binary orderbook storage tradeoffs
- [Supabase Batch Insert Best Practices](https://github.com/orgs/supabase/discussions/11349) -- MEDIUM confidence, community + official
- [Kalshi WS Orderbook Simple (GitHub)](https://github.com/lukepalmdc/kalshi_ws_orderbook_simple) -- MEDIUM confidence, reference implementation
- [websockets Python library](https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html) -- HIGH confidence, official library docs

---
*Architecture research for: KalshiBook -- L2 orderbook collection, storage, and serving*
*Researched: 2026-02-13*
