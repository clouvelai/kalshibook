# Phase 2: REST API + Authentication - Research

**Researched:** 2026-02-14
**Domain:** FastAPI REST API, Supabase Auth, API key management, orderbook reconstruction, rate limiting, OpenAPI documentation
**Confidence:** HIGH

## Summary

Phase 2 builds an authenticated FastAPI REST API serving historical orderbook data from the Phase 1 Postgres schema. The core technical challenge is orderbook reconstruction: given a base snapshot and subsequent deltas, reconstruct the orderbook state at any arbitrary timestamp. The project already uses asyncpg for direct SQL (no ORM) and Pydantic v2 for models, so FastAPI integrates naturally with zero new paradigm.

The authentication layer uses Supabase for user management (signup/login) and a custom `api_keys` table with SHA-256 hashed keys (prefixed `kb-`) validated via a FastAPI dependency. Rate limiting uses SlowAPI with in-memory storage for now (Redis deferred to Phase 3 when billing requires distributed state). Developer experience comes free from FastAPI: OpenAPI 3.1 auto-generated at `/openapi.json`, Swagger/ReDoc docs at `/docs` and `/redoc`, plus hand-authored `/llms.txt` and `/llms-full.txt` for AI agent discovery.

**Primary recommendation:** Build the API as a new `src/api/` package alongside the existing `src/collector/`, sharing `src/shared/` for config and DB. Use FastAPI's lifespan for asyncpg pool management, dependency injection for auth, and cursor-based pagination for delta queries.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Agent-first API design -- Tavily (tavily.com) as the reference product
- Consistent with Kalshi API conventions where it makes sense (field names, market identifiers)
- Every endpoint must work well for programmatic/automated consumers (AI agents, trading bots)
- API must support backtesting workflows: query orderbook state at any historical timestamp for any market
- Tavily-style flat endpoints (e.g., `/orderbook`, `/deltas`, `/markets`) -- no `/v1/` prefix
- POST for complex queries (time ranges, filters), GET for simple lookups
- If versioning becomes needed later, handle via headers or new endpoints -- not URL prefixes
- Supabase for user management (signup, login, password reset)
- API keys generated per user, sent via header (Tavily uses `Authorization: Bearer tvly-KEY`)
- Keys prefixed with `kb-` for easy identification (like Tavily's `tvly-` prefix)
- Key management endpoints: create, list, revoke
- Generous defaults for now -- billing isn't wired until Phase 3
- Include standard rate-limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset) so clients are ready when limits tighten
- 429 responses with clear retry-after when exceeded

### Claude's Discretion

- Exact field naming for orderbook responses (mirror Kalshi vs cleaner schema) -- optimize for agent consumption and backtesting clarity
- Response pagination strategy for delta queries
- Orderbook reconstruction endpoint design (how timestamp is specified, depth levels)
- Market metadata endpoint scope
- Error response body structure (follow Tavily's patterns as guide)
- OpenAPI spec generation approach
- /llms.txt content and structure

### Deferred Ideas (OUT OF SCOPE)

- None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.129.0 | Web framework, OpenAPI generation, dependency injection | Built-in OpenAPI 3.1, async-native, Pydantic v2 integration, auto-generates docs |
| uvicorn | >=0.34.0 | ASGI server | Standard FastAPI production server, async event loop |
| asyncpg | >=0.31.0 | PostgreSQL async driver | Already in project (Phase 1), direct SQL, highest performance |
| pydantic | >=2.12.5 | Request/response models, validation | Already in project, FastAPI native integration |
| pydantic-settings | >=2.12.0 | Environment configuration | Already in project for Settings class |
| structlog | >=25.5.0 | Structured logging | Already in project (Phase 1) |
| orjson | >=3.11.7 | Fast JSON serialization | Already in project, 3-10x faster than stdlib json |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| slowapi | >=0.1.9 | Rate limiting middleware | Per-key rate limiting with X-RateLimit headers |
| supabase | >=2.28.0 | Supabase client (auth operations) | User signup/login/password-reset via Supabase Auth |
| httpx | >=0.28.1 | HTTP client | Already in project, used by supabase-py internally |
| python-multipart | >=0.0.18 | Form data parsing | Required by FastAPI for form-based auth endpoints |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| slowapi | Custom middleware | SlowAPI handles all edge cases (headers, 429 responses, storage backends), <1ms overhead |
| asyncpg (raw SQL) | SQLAlchemy async | ORM overhead unnecessary -- queries are few and performance-critical for reconstruction |
| In-memory rate limit storage | Redis | Redis needed for distributed rate limiting in Phase 3, but overkill for single-process Phase 2 |
| SHA-256 key hashing | bcrypt | SHA-256 is fast (good for API key lookups where we need prefix-based queries); bcrypt is slow by design (better for passwords, not API keys verified on every request) |

**Installation:**
```bash
uv add fastapi uvicorn slowapi supabase python-multipart
```

Note: asyncpg, pydantic, pydantic-settings, structlog, orjson, httpx already in pyproject.toml from Phase 1.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── api/                    # Phase 2: REST API
│   ├── __init__.py
│   ├── main.py             # FastAPI app, lifespan, middleware
│   ├── deps.py             # Dependency injection (auth, db pool)
│   ├── models.py           # Pydantic request/response models
│   ├── errors.py           # Error envelope, exception handlers
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── orderbook.py    # POST /orderbook (reconstruction)
│   │   ├── deltas.py       # POST /deltas (raw delta queries)
│   │   ├── markets.py      # GET /markets, GET /markets/{ticker}
│   │   └── keys.py         # POST /keys, GET /keys, DELETE /keys/{id}
│   └── services/
│       ├── __init__.py
│       ├── reconstruction.py  # Orderbook reconstruction logic
│       └── auth.py            # API key generation, hashing, validation
├── collector/              # Phase 1: existing
│   └── ...
└── shared/                 # Shared modules
    ├── config.py           # Settings (extend with API config)
    └── db.py               # Connection pool (reuse)
```

### Pattern 1: FastAPI Lifespan for asyncpg Pool

**What:** Use FastAPI's lifespan context manager to create/close the asyncpg connection pool. The existing `src/shared/db.py` pool management works directly -- just call `create_pool()` on startup, `close_pool()` on shutdown.

**When to use:** Always -- this is the standard pattern for managing database connections in FastAPI.

**Example:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.shared.db import create_pool, close_pool
from src.shared.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = await create_pool(settings.database_url)
    app.state.pool = pool
    yield
    await close_pool()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Dependency Injection for API Key Auth

**What:** A FastAPI `Depends()` function extracts the API key from the request header, validates it against the database (hashed lookup), and returns the authenticated user/key record. Endpoints that require auth declare this dependency.

**When to use:** Every authenticated endpoint (all data endpoints).

**Example:**
```python
from fastapi import Depends, Header, HTTPException
from src.shared.db import get_pool

async def get_api_key(
    authorization: str = Header(..., alias="Authorization")
) -> dict:
    # Extract "Bearer kb-..." from header
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key.startswith("kb-"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    # Hash and lookup
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, name, rate_limit FROM api_keys WHERE key_hash = $1 AND revoked_at IS NULL",
            key_hash,
        )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return dict(row)

# Usage in endpoint
@app.post("/orderbook")
async def get_orderbook(request: OrderbookRequest, key: dict = Depends(get_api_key)):
    ...
```

### Pattern 3: Structured Error Envelope (Tavily-style)

**What:** All API responses -- success and error -- use a consistent JSON structure. Errors include a machine-readable error code, human-readable message, and request ID for debugging.

**When to use:** Every response from the API.

**Example:**
```python
# Success responses include data + metadata
{
    "data": { ... },
    "request_id": "req_abc123",
    "response_time": 0.045
}

# Error responses follow Tavily's pattern
{
    "error": {
        "code": "invalid_api_key",
        "message": "The provided API key is invalid or has been revoked.",
        "status": 401
    },
    "request_id": "req_abc123"
}
```

### Pattern 4: Orderbook Reconstruction via SQL

**What:** To reconstruct the orderbook at timestamp T for market M: (1) find the most recent snapshot before T, (2) fetch all deltas between the snapshot and T, (3) apply deltas to the snapshot in sequence order. This can be done in a single SQL query using a CTE + JSONB aggregation, or as a two-step query executed in Python.

**When to use:** The `/orderbook` endpoint.

**Algorithm:**
```
1. SELECT the most recent snapshot WHERE market_ticker = M AND captured_at <= T
   ORDER BY captured_at DESC LIMIT 1
2. SELECT all deltas WHERE market_ticker = M
   AND ts > snapshot.captured_at AND ts <= T
   ORDER BY seq ASC
3. Start with snapshot.yes_levels and snapshot.no_levels (JSONB arrays of [price, qty])
4. For each delta: find the price level on the correct side, add delta_amount to quantity
   - If quantity becomes 0, remove the level
   - If price doesn't exist, add a new level
5. Return the reconstructed orderbook sorted by price
```

**Performance notes:**
- The `idx_snapshots_ticker_time` index makes step 1 fast (btree on market_ticker, captured_at DESC)
- The `idx_deltas_ticker_ts` index makes step 2 fast (btree on market_ticker, ts)
- Periodic snapshots (every 300s from collector) limit the number of deltas to replay
- For a 5-minute snapshot interval, worst case is ~300s of deltas (~hundreds of rows typically)

### Pattern 5: Cursor-Based Pagination for Deltas

**What:** Use keyset/cursor pagination instead of OFFSET for delta queries. The cursor is a composite of `(ts, id)` to handle ties on timestamp. This provides O(1) performance regardless of page depth.

**When to use:** The `/deltas` endpoint.

**Example:**
```python
# First page
SELECT * FROM deltas
WHERE market_ticker = $1 AND ts >= $2 AND ts <= $3
ORDER BY ts ASC, id ASC
LIMIT $4

# Next page (cursor = last row's ts + id)
SELECT * FROM deltas
WHERE market_ticker = $1 AND ts >= $2 AND ts <= $3
  AND (ts, id) > ($5, $6)
ORDER BY ts ASC, id ASC
LIMIT $4
```

### Anti-Patterns to Avoid
- **OFFSET pagination for deltas:** Degrades linearly with page depth. Deltas are high-volume (millions of rows). Always use cursor pagination.
- **ORM for reconstruction queries:** The reconstruction algorithm requires precise control over query structure and JSONB manipulation. Raw SQL via asyncpg is clearer and faster.
- **Storing full API keys in the database:** Never store plaintext keys. Store SHA-256 hash only. The raw key is shown once at creation time, never retrievable again.
- **Creating per-request Supabase clients:** Expensive. Create one admin client on startup and reuse it with per-request JWT headers for RLS.
- **Validating API keys via Supabase Auth JWT verification:** API keys are NOT JWTs -- they're opaque tokens in a custom table. Supabase Auth is only for user signup/login. API key validation is a simple hash lookup.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | Custom middleware with counters | SlowAPI (slowapi) | Handles token bucket, sliding window, headers, 429 responses, storage backends |
| OpenAPI spec | Manual JSON schema | FastAPI auto-generation | FastAPI generates OpenAPI 3.1 from route decorators + Pydantic models automatically |
| API docs UI | Custom docs page | FastAPI Swagger (/docs) + ReDoc (/redoc) | Built-in, auto-generated, zero config |
| CORS handling | Manual header injection | FastAPI CORSMiddleware | Handles preflight, allowed origins, credentials correctly |
| Request validation | Manual field checks | Pydantic models in FastAPI | Type coercion, validation errors, OpenAPI schema generation -- all automatic |
| User signup/login | Custom auth system | Supabase Auth (supabase-py) | Email confirmation, password reset, session management, JWT tokens -- production-ready |
| API key generation | Custom random string | `secrets.token_urlsafe(32)` with `kb-` prefix | Cryptographically secure, URL-safe, 256-bit entropy |

**Key insight:** FastAPI + Pydantic gives you validation, serialization, OpenAPI spec, and docs UI with zero extra work. The only custom logic needed is orderbook reconstruction and API key management.

## Common Pitfalls

### Pitfall 1: Reconstruction Accuracy with Overlapping Deltas
**What goes wrong:** Reconstruction returns wrong orderbook state because deltas are applied out of order or a snapshot is missed.
**Why it happens:** Deltas must be applied in strict sequence order (not just timestamp order). Multiple deltas can share the same timestamp but have different sequence numbers.
**How to avoid:** Always ORDER BY seq ASC when fetching deltas for reconstruction. Use the snapshot's `seq` as the starting point and verify continuity. If any gaps exist in the sequence, flag the reconstruction as potentially inaccurate.
**Warning signs:** Negative quantities appearing in reconstructed orderbook, total quantities diverging from known snapshots.

### Pitfall 2: API Key Timing Attacks
**What goes wrong:** An attacker can determine valid key prefixes by measuring response time differences between valid-prefix and invalid-prefix keys.
**Why it happens:** Hash comparison short-circuits on first differing byte.
**How to avoid:** Use `hmac.compare_digest()` for constant-time comparison when verifying hashes. Also: always perform the full hash computation even for obviously invalid keys (wrong prefix length, etc.) to avoid timing leaks.
**Warning signs:** Variable response times for different invalid keys.

### Pitfall 3: Missing Partition for Delta Queries
**What goes wrong:** Query returns 0 results or errors because the partition for the requested date range doesn't exist.
**Why it happens:** Deltas are daily-partitioned. If the collector hasn't run for that date, or partition creation failed, the partition may not exist.
**How to avoid:** Query the deltas table directly (Postgres handles missing partitions gracefully by returning empty results). For time ranges spanning multiple days, the planner automatically routes to the correct partitions. Test with date ranges that cross partition boundaries.
**Warning signs:** Queries for recent dates return empty when data should exist.

### Pitfall 4: SlowAPI Key Function Returns None
**What goes wrong:** All requests share a single rate-limit bucket, causing legitimate users to be rate-limited by others' traffic.
**Why it happens:** The SlowAPI `key_func` returns `None` or a constant when the API key header is missing.
**How to avoid:** The key function should return the API key (or a hash of it) for authenticated requests, and the IP address for unauthenticated requests. Never return None.
**Warning signs:** 429 responses for users who haven't made many requests.

### Pitfall 5: Large Orderbook Reconstructions Block the Event Loop
**What goes wrong:** A reconstruction request for a market with thousands of deltas takes seconds, blocking other requests.
**Why it happens:** Python's asyncio is single-threaded. CPU-bound delta application in Python blocks the event loop.
**How to avoid:** The delta application loop is small (iterate list, update dict) and typically processes <1000 deltas. For extreme cases, consider doing the aggregation in SQL. Monitor P99 latency and add a maximum delta count limit if needed.
**Warning signs:** Request latency spikes correlated with large time-range reconstruction requests.

### Pitfall 6: Supabase Auth Client Misuse
**What goes wrong:** Auth operations fail or are slow because a new Supabase client is created per request.
**Why it happens:** The supabase-py client creates an httpx session internally. Creating many clients leaks connections.
**How to avoid:** Create a single Supabase admin client (with service_role key) during app startup via lifespan. Use it for all auth admin operations (creating users, verifying tokens). For user-facing auth (signup/login), the client handles it directly.
**Warning signs:** Connection pool exhaustion, slow auth responses, httpx warnings in logs.

## Code Examples

Verified patterns from official sources and existing codebase:

### FastAPI App Setup with Lifespan
```python
# Source: FastAPI docs (https://fastapi.tiangolo.com/advanced/events/)
# Adapted for existing src/shared/db.py pattern
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from src.shared.config import get_settings
from src.shared.db import create_pool, close_pool

def get_key_from_request(request):
    """Extract API key for rate limiting, fall back to IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer kb-"):
        return auth  # Rate limit by full key
    return get_remote_address(request)

limiter = Limiter(key_func=get_key_from_request, headers_enabled=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await create_pool(settings.database_url)
    yield
    await close_pool()

app = FastAPI(
    title="KalshiBook API",
    description="Historical L2 orderbook data for Kalshi prediction markets",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Key Generation and Storage
```python
# Source: Python secrets module (https://docs.python.org/3/library/secrets.html)
# Pattern: Supabase API key management guides
import secrets
import hashlib

def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, key_hash).

    The raw key is shown once to the user. Only the hash is stored.
    """
    raw_key = "kb-" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash
```

### API Key Table Migration
```sql
-- Custom API keys table (not Supabase Auth keys)
-- References auth.users for user management via Supabase
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,  -- first 7 chars for display: "kb-abc..."
    name TEXT NOT NULL DEFAULT 'Default',
    rate_limit INT NOT NULL DEFAULT 100,  -- requests per minute
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_hash ON api_keys (key_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_user ON api_keys (user_id);
```

### Orderbook Reconstruction Query
```python
# Two-step reconstruction: fetch snapshot, then apply deltas
async def reconstruct_orderbook(
    pool, market_ticker: str, at_timestamp: datetime
) -> dict | None:
    async with pool.acquire() as conn:
        # Step 1: Most recent snapshot before target timestamp
        snapshot = await conn.fetchrow("""
            SELECT captured_at, seq, yes_levels, no_levels
            FROM snapshots
            WHERE market_ticker = $1 AND captured_at <= $2
            ORDER BY captured_at DESC
            LIMIT 1
        """, market_ticker, at_timestamp)

        if snapshot is None:
            return None  # No data for this market before timestamp

        # Step 2: All deltas between snapshot and target
        deltas = await conn.fetch("""
            SELECT price_cents, delta_amount, side, seq
            FROM deltas
            WHERE market_ticker = $1
              AND ts > $2 AND ts <= $3
            ORDER BY seq ASC
        """, market_ticker, snapshot["captured_at"], at_timestamp)

    # Step 3: Apply deltas to snapshot
    yes_book = {level[0]: level[1] for level in snapshot["yes_levels"]}
    no_book = {level[0]: level[1] for level in snapshot["no_levels"]}

    for delta in deltas:
        book = yes_book if delta["side"] == "yes" else no_book
        price = delta["price_cents"]
        book[price] = book.get(price, 0) + delta["delta_amount"]
        if book[price] <= 0:
            book.pop(price, None)

    return {
        "market_ticker": market_ticker,
        "timestamp": at_timestamp.isoformat(),
        "snapshot_basis": snapshot["captured_at"].isoformat(),
        "deltas_applied": len(deltas),
        "yes": sorted(
            [{"price": p, "quantity": q} for p, q in yes_book.items()],
            key=lambda x: x["price"], reverse=True
        ),
        "no": sorted(
            [{"price": p, "quantity": q} for p, q in no_book.items()],
            key=lambda x: x["price"], reverse=True
        ),
    }
```

### Response Models (Pydantic v2)
```python
from pydantic import BaseModel, Field
from datetime import datetime

class OrderbookLevel(BaseModel):
    price: int = Field(description="Price in cents (1-99)")
    quantity: int = Field(description="Total quantity at this price level")

class OrderbookResponse(BaseModel):
    market_ticker: str = Field(description="Kalshi market ticker")
    timestamp: str = Field(description="Orderbook state as-of this ISO 8601 timestamp")
    snapshot_basis: str = Field(description="Timestamp of the underlying snapshot used for reconstruction")
    deltas_applied: int = Field(description="Number of deltas applied to reach this state")
    yes: list[OrderbookLevel] = Field(description="Yes side levels, sorted by price descending")
    no: list[OrderbookLevel] = Field(description="No side levels, sorted by price descending")

class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    status: int = Field(description="HTTP status code")

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str

class PaginatedDeltasResponse(BaseModel):
    data: list[dict]
    next_cursor: str | None = Field(description="Cursor for next page, null if no more results")
    has_more: bool
    total_count: int | None = Field(description="Approximate total count, null if expensive to compute")
    request_id: str
    response_time: float
```

### llms.txt Structure
```markdown
# KalshiBook API

> Historical L2 orderbook data API for Kalshi prediction markets. Query reconstructed orderbook state at any timestamp, raw deltas, and market metadata.

KalshiBook provides programmatic access to historical Kalshi orderbook data for backtesting trading strategies and building automated trading systems.

## API Reference
- [OpenAPI Spec](/openapi.json): Full API specification
- [Interactive Docs](/docs): Swagger UI for testing endpoints
- [ReDoc](/redoc): Alternative API documentation

## Endpoints
- [POST /orderbook](/docs#/orderbook): Reconstruct orderbook state at any historical timestamp
- [POST /deltas](/docs#/deltas): Query raw orderbook deltas by market and time range
- [GET /markets](/docs#/markets): List available markets with data coverage dates
- [GET /markets/{ticker}](/docs#/markets): Get market metadata and contract details

## Authentication
- [POST /keys](/docs#/keys): Create a new API key
- [GET /keys](/docs#/keys): List your API keys
- [DELETE /keys/{id}](/docs#/keys): Revoke an API key

## Optional
- [GET /health](/docs#/health): Health check endpoint
```

## Discretion Recommendations

The following areas were marked as "Claude's Discretion" in CONTEXT.md. Here are researched recommendations:

### Field Naming: Use Kalshi Names with Clarity Additions
**Recommendation:** Use Kalshi's `market_ticker` (not `ticker` or `symbol`), `yes`/`no` sides (not `bid`/`ask`), and `price` in cents. Add descriptive fields agents need: `price` (integer cents), `quantity` (integer contracts). This mirrors Kalshi's conventions while being self-describing for agents.
**Rationale:** Agents working with Kalshi data will expect Kalshi naming. Prediction market orderbooks have `yes`/`no` sides, not `bid`/`ask`. Adding natural language field descriptions in the Pydantic model flows into OpenAPI spec automatically.

### Pagination: Cursor-Based with (ts, id) Composite
**Recommendation:** Cursor-based pagination using base64-encoded `(timestamp, id)` tuple. Default page size 100, max 1000. Return `next_cursor` and `has_more` in response.
**Rationale:** Deltas are high-volume time-series data. OFFSET pagination degrades at depth. Cursor on `(ts, id)` leverages the existing `idx_deltas_ticker_ts` index and handles timestamp ties correctly.

### Reconstruction Endpoint: POST with Explicit Timestamp
**Recommendation:** `POST /orderbook` with body `{"market_ticker": "TICKER", "timestamp": "2026-02-14T12:00:00Z"}`. Optional `depth` parameter to limit levels returned (default: all levels).
**Rationale:** POST because the query is semantically complex (not a simple resource lookup). ISO 8601 timestamp is unambiguous across timezones. Depth limiting is useful for agents that only need top-of-book.

### Market Metadata: Coverage Dates + Kalshi Fields
**Recommendation:** `GET /markets` returns list with ticker, title, event_ticker, status, first_data_at, last_data_at. `GET /markets/{ticker}` adds full metadata (rules, strike_price, category, total snapshots/deltas counts).
**Rationale:** Coverage dates are critical for backtesting -- agents need to know which markets have data and for what period. The existing `markets` table already has most fields. Add computed `first_data_at`/`last_data_at` from snapshots/deltas tables.

### Error Response: Tavily-Inspired Envelope
**Recommendation:** Errors return `{"error": {"code": "string", "message": "string", "status": int}, "request_id": "string"}`. Error codes are snake_case machine-readable strings: `invalid_api_key`, `rate_limit_exceeded`, `market_not_found`, `invalid_timestamp`, `no_data_available`.
**Rationale:** Tavily returns `{"detail": {"error": "message"}}`. KalshiBook improves on this with separate code/message fields (machine-readable + human-readable) and request_id for debugging.

### OpenAPI: Built-in FastAPI Generation
**Recommendation:** Use FastAPI's automatic OpenAPI 3.1 generation. Add rich metadata via Pydantic Field descriptions and FastAPI route docstrings. Serve at `/openapi.json` (default). Add tags for endpoint grouping.
**Rationale:** FastAPI generates OpenAPI spec from code with zero config. Pydantic v2 Field descriptions become schema descriptions. Route docstrings become operation descriptions. This is the standard approach -- no extra tooling needed.

### llms.txt: Markdown Index with Endpoint Descriptions
**Recommendation:** Serve `/llms.txt` as a static markdown file listing all endpoints with brief descriptions and links to `/openapi.json` for full spec. Serve `/llms-full.txt` with the full OpenAPI spec content inlined as markdown.
**Rationale:** The llms.txt spec requires a markdown file with H1 title, optional blockquote summary, and H2 sections with link lists. The "full" variant includes all documentation content for LLMs that want to load everything at once.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastAPI on_event decorator | Lifespan context manager | FastAPI 0.93+ (2023) | on_event is deprecated, lifespan is the standard |
| Pydantic v1 .dict() / .schema() | Pydantic v2 .model_dump() / .model_json_schema() | Pydantic 2.0 (2023) | FastAPI 0.129+ requires Pydantic >=2.7 |
| OFFSET pagination | Cursor/keyset pagination | Industry standard shift ~2020 | O(1) vs O(n) for deep pages |
| Supabase anon/service_role keys | Publishable/secret keys | Supabase 2025 migration | Old keys still work, new projects use new format |
| Manual OpenAPI JSON | Auto-generated from code | FastAPI launch (2018) | No manual spec maintenance needed |

**Deprecated/outdated:**
- FastAPI `@app.on_event("startup")` / `@app.on_event("shutdown")` -- use lifespan instead
- Pydantic v1 `orm_mode` -- replaced by `from_attributes` in v2
- Supabase `anon` key -- being replaced by `publishable` key (backward compatible through 2026)

## Open Questions

1. **Supabase Auth SDK async support for signup/login flows**
   - What we know: `supabase-py` >=2.2.0 has `acreate_client()` for async operations. Auth operations (sign_up, sign_in_with_password) are available.
   - What's unclear: Whether the auth endpoints in the API should proxy Supabase Auth directly, or if signup/login should happen exclusively through a future dashboard (Phase 5). The CONTEXT says "Supabase for user management" but doesn't specify where the signup UI lives.
   - Recommendation: Expose minimal auth endpoints in the API (`POST /auth/signup`, `POST /auth/login`) that proxy to Supabase Auth. This allows headless/agent signups before the dashboard exists. Phase 5 dashboard will also use Supabase Auth directly.

2. **Rate limit defaults before billing (Phase 3)**
   - What we know: "Generous defaults" per CONTEXT. No billing enforcement yet.
   - What's unclear: Exact numbers for default rate limits.
   - Recommendation: 100 requests/minute per API key as default. This is generous for development and testing but prevents abuse. Configurable per-key in the database for flexibility. Phase 3 will tie rate limits to subscription tiers.

3. **Orderbook reconstruction for timestamps before any snapshot**
   - What we know: The collector takes periodic snapshots (every 300s). If a user queries a timestamp before the first snapshot for a market, no reconstruction is possible.
   - What's unclear: Should the API return an error or the earliest available state?
   - Recommendation: Return a structured error with `code: "no_data_available"` and include the earliest available timestamp in the error payload so the agent knows when to query from.

## Sources

### Primary (HIGH confidence)
- FastAPI official docs (https://fastapi.tiangolo.com/) -- lifespan, dependencies, OpenAPI, CORS
- Pydantic v2 docs (https://docs.pydantic.dev/) -- model validation, Field descriptions
- Python secrets module (https://docs.python.org/3/library/secrets.html) -- token_urlsafe
- Existing codebase: `src/shared/db.py`, `src/collector/writer.py`, `src/collector/models.py` -- asyncpg patterns, data models, schema
- Supabase migrations: `supabase/migrations/` -- exact table schemas for snapshots, deltas, markets
- llms.txt specification (https://llmstxt.org/) -- file format and structure

### Secondary (MEDIUM confidence)
- Tavily API docs (https://docs.tavily.com/documentation/api-reference/endpoint/search) -- error codes, response envelope patterns
- SlowAPI docs (https://slowapi.readthedocs.io/) -- Limiter API, key_func, headers_enabled
- Supabase Auth Python reference (https://supabase.com/docs/reference/python/auth-signup) -- sign_up, sign_in_with_password
- MakerKit Supabase API key guide (https://makerkit.dev/blog/tutorials/supabase-api-key-management) -- table schema, bcrypt vs SHA-256, prefix pattern
- Supabase API keys gist (https://gist.github.com/j4w8n/25d233194877f69c1cbf211de729afb2) -- Vault-based JWT key management

### Tertiary (LOW confidence)
- SlowAPI project status: version 0.1.9, appears low-maintenance but stable and widely used in production. If maintenance becomes a concern, custom middleware is straightforward since the rate limiting logic is simple.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- FastAPI, asyncpg, Pydantic already in project; well-documented, stable ecosystem
- Architecture: HIGH -- follows established FastAPI patterns; reconstruction algorithm is straightforward given existing schema
- Pitfalls: HIGH -- based on actual codebase analysis (partition structure, schema, asyncpg patterns)
- Discretion areas: MEDIUM -- recommendations based on Tavily patterns and best practices, but specific field naming and pagination details need validation during implementation

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable domain, 30-day validity)
