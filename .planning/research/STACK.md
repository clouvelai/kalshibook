# Stack Research

**Domain:** Monetized market data API (websocket collection + storage + API serving + billing)
**Researched:** 2026-02-13
**Confidence:** MEDIUM-HIGH (core stack HIGH, Supabase Realtime for Python LOW)

## Decision Framework

This project has three distinct runtime contexts with different requirements:

1. **Collector** -- Long-running Python process on Railway. Connects to Kalshi websocket, receives orderbook snapshots/deltas, writes to Supabase/Postgres. Must be resilient, auto-reconnecting, and crash-safe.
2. **API Server** -- Serves REST endpoints and outbound websocket feeds to paying subscribers. Handles auth, rate limiting, usage metering. Deployed on Railway.
3. **Billing/Auth infrastructure** -- Supabase Auth for user identity, Stripe for payments, custom middleware to enforce tier limits.

The stack choices below are organized around these three contexts.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.12+ | Runtime | Project already uses Python. 3.12 has significant asyncio performance improvements. 3.13 acceptable but 3.12 is the safe production target. | HIGH |
| FastAPI | ~0.129.0 | REST API + WS server | Already established in codebase patterns. Native async, OpenAPI docs auto-generated (critical for API-as-product), first-class websocket support via `@app.websocket()`. PostgREST cannot handle custom business logic (usage metering, tier enforcement, orderbook reconstruction). | HIGH |
| Pydantic | ~2.12.5 | Data validation/serialization | FastAPI's native validation layer. Orderbook snapshots/deltas need strict schema validation. V2 is significantly faster than V1 (Rust core). | HIGH |
| uvicorn | ~0.40.0 | ASGI server | Standard production server for FastAPI. Install with `uvicorn[standard]` to get uvloop + httptools for ~2x throughput. | HIGH |

### Database & Storage

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Supabase (hosted) | Current | Managed Postgres + Auth + Realtime infra | Removes ops burden. Postgres 17 with connection pooling (Supavisor), built-in auth with JWT/RLS, dashboard/Studio for debugging. Direct Postgres connection available for bulk writes from collector. | HIGH |
| PostgreSQL | 17 | Primary datastore | Supabase uses PG17. JSONB for orderbook snapshots, BTREE indexes on (market_ticker, timestamp) for time-range queries. Partitioning by time range for data lifecycle management. | HIGH |
| supabase-py | ~2.28.0 | Supabase Python client | Auth operations, simple CRUD, edge function invocation. Use for auth flows and admin operations. Do NOT use for high-throughput collector writes (use direct PG connection instead). | MEDIUM |
| asyncpg | ~0.30.0 | Direct async Postgres driver | 5x faster than psycopg3 for the simple, high-frequency INSERTs the collector performs. Binary protocol, zero-copy. Use for collector writes and API reads where PostgREST is insufficient. | HIGH |

### Websocket Collection (Kalshi)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| websockets | ~16.0 | Kalshi WS client | Production-grade asyncio websocket library. Kalshi's own docs show raw websocket usage. Auto-reconnection via `websockets.connect` with retry. Mature, well-tested, SOCKS proxy support. | HIGH |
| orjson | ~3.11.7 | Fast JSON parsing | Orderbook deltas arrive as JSON at high frequency. orjson is 10-20x faster than stdlib json, written in Rust. Direct FastAPI integration for response serialization too. | HIGH |

### API Serving (Outbound)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| FastAPI (websockets) | (same) | Outbound WS feeds | FastAPI's `@app.websocket()` handles subscriber connections. ConnectionManager pattern for broadcasting orderbook updates to multiple subscribers. | HIGH |
| redis (redis-py) | ~5.2.0+ | Pub/sub for WS broadcasting | If scaling to multiple API server instances, Redis pub/sub coordinates broadcasts. The `redis.asyncio` module (formerly aioredis, now merged) provides async support. Single-instance MVP can skip this. | MEDIUM |

### Authentication & Billing

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Supabase Auth | (managed) | User identity + JWT | Handles signup, login, JWT issuance, token refresh. Custom claims hook for injecting subscription tier into JWT. RLS policies enforce data access. No custom auth code needed. | HIGH |
| stripe | ~14.3.0 | Billing + subscriptions | Industry standard. Usage-based billing via Meter Events API (1000 calls/sec). Webhooks for subscription lifecycle. Python SDK is mature and well-typed. | HIGH |
| httpx | ~0.28.1 | HTTP client (Stripe webhooks, Kalshi REST) | Modern async/sync HTTP client. Use for Kalshi REST API calls (market metadata), Stripe API calls where SDK doesn't suffice, health checks. | HIGH |

### Infrastructure

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Railway | (managed) | Hosting for collector + API | Supports long-running processes, WebSocket outbound/inbound, Docker containers, environment variables, zero-downtime deploys. Cost-effective for always-on services. | HIGH |
| Docker | Latest | Container packaging | Railway deploys from Dockerfile. Ensures reproducible builds. Multi-stage build for small images. | HIGH |
| uv | ~0.10.2 | Package management | Already in project. 10-100x faster than pip. Universal lockfile, Cargo-style workspaces. Use for all dependency management. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| structlog | ~25.5.0 | Structured logging | Always. JSON-formatted logs for Railway log aggregation. Async-safe with `ainfo()`. Context variables for request tracing. | HIGH |
| ruff | ~0.15.1 | Linting + formatting | Development. Replaces black, flake8, isort in one tool. 100x faster. | HIGH |
| pytest | ~8.x | Testing | All tests. Already in project patterns. | HIGH |
| pytest-asyncio | ~1.3.0 | Async test support | Testing async collector/API code. V1.0+ has cleaner event loop handling. | HIGH |
| python-dotenv | ~1.0.x | Env var loading | Local development only. Railway injects env vars natively. | MEDIUM |
| tenacity | ~9.x | Retry logic | Collector reconnection, Stripe webhook retries, transient PG failures. Decorator-based, asyncio-native. | HIGH |
| APScheduler | ~3.11.x | Scheduled tasks | Usage reporting to Stripe (batch meter events), data retention cleanup, health check pings. AsyncIOScheduler integrates with the event loop. | MEDIUM |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package management, virtualenv, Python version management | Replace pip, pip-tools, pyenv. Use `uv add`, `uv sync`, `uv run`. |
| ruff | Lint + format | Configure in `pyproject.toml`. One tool replaces black + flake8 + isort. |
| pytest + pytest-asyncio | Testing | `pytest.mark.asyncio` for async tests. Mock websocket connections for collector tests. |
| Supabase CLI | Local Postgres, Auth, Realtime | `supabase start` gives local PG on port 54322. Use for migration development. |
| Docker Compose | Local multi-service dev | Collector + API + Supabase local stack for integration testing. |

---

## Critical Architecture Decisions

### 1. Custom FastAPI API vs Supabase PostgREST

**Decision: Custom FastAPI for ALL customer-facing endpoints.**

**Rationale (HIGH confidence):**
- PostgREST exposes raw table structure. Orderbook reconstruction requires business logic (applying deltas to snapshots) that cannot live in PostgREST.
- Usage metering (counting API calls per user for Stripe billing) requires middleware. PostgREST has no middleware concept.
- Rate limiting per subscription tier requires request-level logic. PostgREST rate limiting is global, not per-user-tier.
- API documentation (OpenAPI/Swagger) is auto-generated by FastAPI and is a selling point for an API product.
- PostgREST is fine for internal admin queries from Supabase Studio. Not for the customer API.

**What PostgREST IS useful for:**
- Supabase Dashboard/Studio queries during development.
- Simple admin CRUD (user management, market metadata) if building a dashboard later.

### 2. Custom FastAPI WebSocket Server vs Supabase Realtime

**Decision: Custom FastAPI websocket server for subscriber feeds.**

**Rationale (HIGH confidence):**
- Supabase Realtime pushes raw Postgres changes. Subscribers need reconstructed orderbook state, not raw INSERT events.
- The Python realtime client (`realtime-py`) is effectively inactive -- no new releases in 12+ months, known connection timeout issues (GitHub issue #236), and sync client doesn't support realtime at all.
- Supabase Realtime has an 8KB NOTIFY payload limit. Orderbook snapshots can exceed this.
- Custom WS server enables: subscription-tier-based throttling, custom message formats, backpressure handling, connection authentication via API keys.
- Supabase Realtime's Postgres Changes feature is disabled by default on new projects due to performance concerns, and Supabase themselves recommend Broadcast for most use cases.

**Where Supabase Realtime COULD be used (future):**
- Internal: Collector notifying API server of new data (via Broadcast, not Postgres Changes). But even this is simpler with Redis pub/sub or direct asyncio queues.

### 3. Direct Postgres (asyncpg) vs supabase-py for Data Access

**Decision: asyncpg for collector writes and API reads. supabase-py for auth operations only.**

**Rationale (HIGH confidence):**
- Collector writes thousands of orderbook deltas per second. HTTP overhead of PostgREST/supabase-py is unacceptable. asyncpg uses Postgres binary protocol with zero-copy, 5x faster than psycopg3.
- API reads need complex queries (time-range filters, orderbook reconstruction joins). Raw SQL via asyncpg is more expressive and performant than the PostgREST query builder.
- supabase-py is the right tool for auth operations (sign up, sign in, token verification) since it wraps Supabase Auth's REST API cleanly.
- Connection to Supabase Postgres is via direct connection string (port 5432 on hosted Supabase, 54322 locally).

### 4. Supabase Auth for User Identity + Custom API Keys for API Access

**Decision: Hybrid. Supabase Auth manages user accounts. Custom API key table for programmatic access.**

**Rationale (HIGH confidence):**
- Algo traders and AI agents need API keys, not OAuth flows. They call `curl -H "X-API-Key: kb_..."`.
- Supabase Auth handles the human side: signup, login, dashboard access, password reset.
- Custom `api_keys` table in Postgres links API keys to user accounts and subscription tiers.
- FastAPI middleware validates API keys on each request, looks up tier, enforces rate limits.
- JWT custom claims hook can inject tier info for dashboard-side RLS policies.

### 5. TimescaleDB Hypertables: NOT for MVP

**Decision: Standard Postgres partitioning for MVP. TimescaleDB is deprecated on Supabase PG17.**

**Rationale (HIGH confidence):**
- TimescaleDB extension is deprecated on Supabase Postgres 17. Only supported on PG15, which reaches Supabase EOL ~May 2026.
- Building on a deprecated extension is a rewrite risk. Standard Postgres table partitioning by time range achieves adequate performance for MVP scale.
- If time-series query performance becomes a bottleneck at scale, migrate to dedicated TimescaleDB instance (not Supabase) or use Postgres native partitioning with proper indexing.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not the Alternative |
|----------|-------------|-------------|------------------------|
| API Framework | FastAPI | Supabase PostgREST | No custom business logic, no middleware, no usage metering, no rate limiting per tier. See Decision #1. |
| API Framework | FastAPI | Django REST Framework | Overkill ORM, sync-first architecture, slower for async WS workloads. Project is already FastAPI-patterned. |
| Realtime feeds | FastAPI WS | Supabase Realtime | Python client is unmaintained, 8KB payload limit, pushes raw DB changes not reconstructed state. See Decision #2. |
| Realtime feeds | FastAPI WS | Socket.IO (python-socketio) | Adds protocol complexity. Raw websockets are simpler for structured data feeds. Socket.IO is for browser apps needing fallbacks. |
| PG Driver | asyncpg | psycopg3 (async) | asyncpg is 5x faster for the simple high-frequency INSERTs the collector needs. psycopg3 wins on DX (row factories, sync/async unified API) but speed matters more here. |
| PG Driver | asyncpg | supabase-py (PostgREST) | HTTP overhead kills throughput for high-frequency writes. PostgREST adds latency per request. See Decision #3. |
| JSON lib | orjson | stdlib json | 10-20x slower. At orderbook delta volume (hundreds/sec), parsing overhead is measurable. |
| JSON lib | orjson | ujson | orjson is 2-4x faster than ujson and better maintained (Rust vs C). |
| Time-series | PG partitioning | TimescaleDB on Supabase | Deprecated on PG17, EOL on PG15 by May 2026. See Decision #5. |
| Kalshi client | Raw websockets | kalshi-python (official SDK) | Official SDK is REST-only. WS needs raw `websockets` library with custom auth headers. |
| Kalshi client | Raw websockets | aiokalshi | WS support still in development. REST-only currently. Not production ready for our WS use case. |
| Hosting | Railway | Fly.io | Railway has simpler DX for long-running processes. Fly.io requires more ops knowledge (machines, volumes). Both support WS. |
| Hosting | Railway | AWS ECS/Lambda | Lambda can't run persistent WS connections. ECS is overkill ops for a single-dev project. |
| Package manager | uv | Poetry | uv is 10-100x faster, already in project, replaces more tools. Poetry is slower and has resolver issues. |
| Package manager | uv | pip + pip-tools | uv does everything they do but faster, with lockfile and Python version management. |
| Auth | Supabase Auth | Auth0/Clerk | Additional vendor dependency and cost. Supabase Auth is free with Supabase and integrates natively with RLS. |
| Billing | Stripe | Paddle/LemonSqueezy | Stripe has the best API for usage-based metered billing (Meter Events API). Paddle/Lemon are for SaaS seats, not API usage tiers. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Supabase PostgREST for customer API | Cannot inject business logic (reconstruction, metering, tier limits). Exposes raw table schema. | FastAPI with asyncpg |
| Supabase Realtime for subscriber WS feeds | Python client unmaintained, 8KB payload limit, raw DB changes not useful directly | FastAPI `@app.websocket()` |
| realtime-py | Inactive maintenance, connection timeout bugs, sync client has no realtime support | Custom websocket broadcasting via FastAPI |
| TimescaleDB on Supabase | Deprecated on PG17, PG15 EOL ~May 2026. Building on deprecated extension = rewrite risk | Postgres native partitioning + proper indexing |
| psycopg2 | Sync-only, legacy. Blocks the event loop. | asyncpg for async, psycopg3 if you ever need sync fallback |
| aiohttp | Heavier than needed, less ecosystem integration with FastAPI. Separate server. | FastAPI (already handles both REST + WS) |
| Celery | Requires Redis/RabbitMQ broker, separate worker processes. Overkill for periodic tasks. | APScheduler (in-process, asyncio-native) |
| SQLAlchemy ORM | Adds abstraction layer over simple queries. Orderbook queries are better as raw SQL. asyncpg is faster without ORM overhead. | asyncpg with raw SQL (parameterized) |
| Flask | Sync-first, no native async/WS support. Wrong paradigm for real-time data API. | FastAPI |
| Supabase Edge Functions for API | Written in Deno/TypeScript, not Python. Would split the codebase across two languages. Cold start latency. | FastAPI on Railway (always-warm, Python) |

---

## Installation

```bash
# Initialize project (if pyproject.toml doesn't exist)
uv init

# Core runtime
uv add fastapi uvicorn[standard] pydantic

# Database
uv add asyncpg supabase

# Websocket collection (Kalshi)
uv add websockets

# JSON performance
uv add orjson

# HTTP client
uv add httpx

# Billing
uv add stripe

# Logging
uv add structlog

# Retry logic
uv add tenacity

# Scheduling
uv add apscheduler

# Environment
uv add python-dotenv

# Dev dependencies
uv add --dev pytest pytest-asyncio ruff
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| FastAPI ~0.129.0 | Pydantic >=2.0, Starlette >=0.40.0 | FastAPI pins Starlette range. Don't install Starlette separately. |
| asyncpg ~0.30.0 | PostgreSQL 9.5-17 | Supabase uses PG17. asyncpg supports it natively. |
| uvicorn[standard] ~0.40.0 | Python 3.9+ | `[standard]` extra installs uvloop + httptools + websockets. |
| Pydantic ~2.12.5 | Python 3.9+ | V2 only. Do NOT use pydantic.v1 imports. |
| supabase-py ~2.28.0 | Python >=3.9 | Wraps auth-py, postgrest-py, realtime-py, storage-py internally. |
| orjson ~3.11.7 | Python 3.10+ | Dropped 3.9 support in recent versions. Ensure Python >=3.10 if using latest orjson. |
| stripe ~14.3.0 | Python 3.6+ | Uses Stripe API version 2026-01-28.clover. |
| websockets ~16.0 | Python 3.9+ | SOCKS proxy support built-in (useful if Railway needs egress proxy). |
| pytest-asyncio ~1.3.0 | pytest >=8.0 | V1.0+ removed `event_loop` fixture. Use `loop_scope` parameter instead. |
| ruff ~0.15.1 | Python 3.9+ (analysis target) | Configure `target-version = "py312"` in pyproject.toml. |

---

## Stack Patterns by Variant

**If MVP (single Railway service, <100 subscribers):**
- Run collector and API server in the same Python process using `asyncio.gather()`.
- No Redis needed. Use in-memory `ConnectionManager` for WS broadcasting.
- Single asyncpg connection pool shared between collector writes and API reads.
- APScheduler for periodic Stripe usage reporting.

**If scaling (multiple Railway services, >100 subscribers):**
- Separate collector and API into distinct Railway services.
- Add Redis for pub/sub between collector and API instances.
- Collector publishes new data to Redis channel, API servers subscribe and broadcast to their local WS clients.
- Connection pool per service, sized appropriately.

**If high-volume (full market coverage, connection pooling):**
- Multiple collector instances, each with its own Kalshi WS connection, covering different market subsets.
- Supabase Supavisor connection pooler enabled (transaction mode).
- Consider dedicated Postgres (not Supabase) if write volume exceeds Supabase plan limits.
- Redis Streams instead of pub/sub for message durability.

---

## Sources

- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/) -- FastAPI v0.129.0 confirmed (HIGH)
- [FastAPI PyPI](https://pypi.org/project/fastapi/) -- version verification (HIGH)
- [supabase-py GitHub](https://github.com/supabase/supabase-py) -- v2.28.0 confirmed (HIGH)
- [supabase PyPI](https://pypi.org/project/supabase/) -- version verification (HIGH)
- [websockets PyPI](https://pypi.org/project/websockets/) -- v16.0 confirmed (HIGH)
- [websockets docs](https://websockets.readthedocs.io/) -- feature verification (HIGH)
- [stripe-python GitHub releases](https://github.com/stripe/stripe-python/releases) -- v14.3.0 confirmed (HIGH)
- [Stripe usage-based billing docs](https://docs.stripe.com/billing/subscriptions/usage-based) -- Meter Events API (HIGH)
- [Pydantic PyPI](https://pypi.org/project/pydantic/) -- v2.12.5 confirmed (HIGH)
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) -- v0.40.0 confirmed (HIGH)
- [asyncpg GitHub](https://github.com/MagicStack/asyncpg) -- 5x faster than psycopg3 claim (MEDIUM -- vendor benchmark)
- [Psycopg 3 vs Asyncpg comparison](https://fernandoarteaga.dev/blog/psycopg-vs-asyncpg/) -- independent benchmark (MEDIUM)
- [orjson PyPI](https://pypi.org/project/orjson/) -- v3.11.7 confirmed (HIGH)
- [Kalshi WebSocket docs](https://docs.kalshi.com/websockets/orderbook-updates) -- orderbook_snapshot/delta format (HIGH)
- [Kalshi WS Connection docs](https://docs.kalshi.com/websockets/websocket-connection) -- auth headers required (HIGH)
- [realtime-py issue #236](https://github.com/supabase/realtime-py/issues/236) -- connection timeout bugs (HIGH)
- [supabase-py issue #909](https://github.com/supabase/supabase-py/issues/909) -- realtime not available in sync client (HIGH)
- [Supabase Realtime docs](https://supabase.com/docs/guides/realtime/postgres-changes) -- 8KB NOTIFY limit, disabled by default (HIGH)
- [Supabase TimescaleDB docs](https://supabase.com/docs/guides/database/extensions/timescaledb) -- deprecated on PG17 (HIGH)
- [Supabase RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security) -- policy patterns (HIGH)
- [Supabase API keys docs](https://supabase.com/docs/guides/api/api-keys) -- publishable/secret key migration (MEDIUM)
- [ruff GitHub](https://github.com/astral-sh/ruff) -- v0.15.1 confirmed (HIGH)
- [structlog PyPI](https://pypi.org/project/structlog/) -- v25.5.0 confirmed (HIGH)
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) -- v1.3.0 confirmed (HIGH)
- [uv GitHub](https://github.com/astral-sh/uv) -- v0.10.2 confirmed (HIGH)
- [redis-py asyncio docs](https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html) -- aioredis merged into redis-py (HIGH)
- [Hacker News: FastAPI + Supabase discussion](https://news.ycombinator.com/item?id=42353177) -- community patterns (LOW)
- [Supabase PostgREST performance](https://supabase.com/docs/guides/api) -- 300% faster than Firebase reads (MEDIUM)
- [Railway platform](https://railway.com/) -- long-running service support confirmed (HIGH)
- [Tavily pricing docs](https://docs.tavily.com/documentation/api-credits) -- credit-based tier model reference (HIGH)

---
*Stack research for: KalshiBook -- Monetized Kalshi L2 Orderbook Data API*
*Researched: 2026-02-13*
