# Project Research Summary

**Project:** KalshiBook -- Monetized Kalshi L2 Orderbook Data API
**Domain:** Market data collection, storage, and serving (prediction markets)
**Researched:** 2026-02-13
**Confidence:** MEDIUM-HIGH

## Executive Summary

KalshiBook is a monetized API product that collects L2 orderbook data from Kalshi's prediction market websocket, stores it with full fidelity, and serves it to algo traders, quants, and AI agents via REST and websocket endpoints. The closest analogues are Tardis.dev (crypto orderbook replay), Databento (MBO/MBP equity data), and Tavily (agent-first API design). The expert approach is event sourcing: capture raw snapshots and deltas from Kalshi's websocket, store them immutably, and reconstruct orderbook state at arbitrary timestamps on read. No one currently offers this for Kalshi, making point-in-time reconstruction the core differentiator.

The recommended stack is Python 3.12+ with FastAPI for both REST and websocket serving, asyncpg for high-throughput Postgres writes, and Supabase as the managed Postgres/Auth layer. Three critical architectural decisions emerged with high confidence: (1) use custom FastAPI for all customer-facing endpoints, not Supabase PostgREST, because orderbook reconstruction and usage metering require application logic; (2) build a custom websocket server for subscriber feeds, not Supabase Realtime, because the Python realtime client is unmaintained and the 8KB NOTIFY limit is too small; (3) use native Postgres partitioning, not TimescaleDB, because TimescaleDB is deprecated on Supabase PG17 with no migration path. Stripe handles billing with a Tavily-style credit system (free tier through enterprise).

The primary risks are data integrity and operational reliability. Silent orderbook corruption from missed websocket deltas is the single most dangerous failure mode -- it produces incorrect data that looks correct, destroying consumer trust. The mitigation is strict sequence validation with automatic re-snapshot on gap detection, implemented from day one. Secondary risks include Supabase write throughput ceilings (mitigated by batched asyncpg writes bypassing PostgREST) and Stripe webhook unreliability (mitigated by idempotent handlers plus a reconciliation cron). The product's value proposition depends entirely on data completeness and correctness; every architectural decision should optimize for these over development speed.

## Key Findings

### Recommended Stack

The stack is organized around three runtime contexts: a long-running collector (Kalshi websocket to Postgres), a FastAPI server (REST + websocket serving), and an auth/billing layer (Supabase Auth + Stripe). All Python, all async.

**Core technologies:**
- **FastAPI + uvicorn[standard]**: REST API + websocket server -- native async, auto-generated OpenAPI docs (critical for an API-as-product), first-class websocket support. PostgREST cannot handle custom business logic.
- **asyncpg**: Direct async Postgres driver -- 5x faster than psycopg3 for the simple, high-frequency INSERTs the collector performs. Binary protocol, zero-copy. Use for all collector writes and API reads.
- **Supabase (hosted Postgres 17)**: Managed database + auth + connection pooling -- removes ops burden, provides Auth with JWT/RLS, direct Postgres connection available for collector writes.
- **websockets**: Kalshi websocket client -- production-grade asyncio websocket library with auto-reconnection. Kalshi's official SDK is REST-only.
- **orjson**: Fast JSON parsing -- 10-20x faster than stdlib json. At orderbook delta volume (hundreds/sec), parsing overhead is measurable.
- **Stripe**: Billing + subscriptions -- usage-based billing via Meter Events API. Python SDK is mature. Credit-based pricing model (Tavily pattern).
- **Pydantic v2**: Data validation -- Rust core, strict schema validation for orderbook data. FastAPI's native layer.
- **Railway**: Hosting -- supports long-running processes, websocket connections, Docker deploys. Cost-effective for always-on services.

**Critical version notes:** Python 3.12+ required (asyncio performance), Pydantic v2 only (no v1 imports), TimescaleDB is NOT available on Supabase PG17.

### Expected Features

**Must have (table stakes):**
- Data collection pipeline (websocket listener for L2 snapshots + deltas)
- Historical orderbook REST API (query state at any timestamp)
- Point-in-time orderbook reconstruction engine (snapshot + delta replay)
- Raw delta stream endpoint (paginated, time-range filtered)
- Market metadata endpoint (ticker, event, status, coverage dates)
- API key authentication (issue, validate, associate with usage)
- Rate limiting with standard response headers (per-key, tier-based)
- Free tier (1,000 credits/month for adoption)
- OpenAPI documentation (auto-generated from FastAPI)
- Consistent JSON error responses (structured error envelope)

**Should have (differentiators):**
- Agent-friendly API design (flat JSON, self-describing endpoints, `/llms.txt`)
- Credit-based pricing with transparent per-endpoint costs
- Real-time websocket streaming (re-broadcast to subscribers)
- Python SDK (auto-generated from OpenAPI)
- MCP server (AI agent tool discovery -- land-grab opportunity)
- Sequence numbers for delta ordering and gap detection

**Defer (v2+):**
- Flat file downloads (CSV/Parquet) -- premium tier feature
- Enterprise tier with custom SLAs
- Full market coverage (connection pooling beyond 1K market limit)
- Derived metrics (spread, mid-price, order imbalance)
- OHLCV candle aggregation (not the product's value prop)
- Multi-exchange aggregation (Polymarket, Manifold -- incompatible data models)
- Trade execution (completely different product, regulatory implications)

### Architecture Approach

The system is a three-layer pipeline: ingestion (Kalshi websocket to Postgres via batched writes), storage (Supabase Postgres with native range partitioning -- daily for deltas, monthly for snapshots), and serving (FastAPI REST + websocket with auth middleware). The collector and API server are separate deployable units on Railway, sharing Postgres as the integration point. For MVP, they can run in a single process via `asyncio.gather()`. The core data model is event sourcing: immutable snapshots + deltas, reconstructed on read.

**Major components:**
1. **WS Connector + Orderbook Processor** -- Authenticates to Kalshi (RSA-PSS), maintains persistent websocket, validates sequence numbers, detects gaps, triggers re-snapshots on corruption
2. **Write Buffer / Batcher** -- Accumulates deltas in memory, flushes to Postgres in 500-1000 row batches every 2-5 seconds via asyncpg (not PostgREST)
3. **Market Discovery** -- Subscribes to `market_lifecycle_v2` channel, auto-subscribes to new markets' orderbook feeds
4. **Reconstruction Service** -- Finds nearest snapshot before target timestamp, applies ordered deltas forward, returns point-in-time orderbook state
5. **API Middleware (Auth + Rate Limiting + Usage)** -- Validates API keys, enforces tier-based rate limits, tracks usage for Stripe metered billing
6. **Stripe Billing Integration** -- Webhook handlers (idempotent), subscription lifecycle management, reconciliation cron as safety net

### Critical Pitfalls

1. **Silent orderbook corruption from missed deltas** -- Validate `seq` on every delta. On any gap, immediately unsubscribe/resubscribe to trigger fresh snapshot. Never serve stale data. Implement periodic REST API reconciliation. This is Phase 1 -- everything downstream depends on data correctness.

2. **Websocket disconnection losing data windows** -- Implement heartbeat watchdog (15s timeout), force reconnect with gap logging, record gaps in a `data_gaps` table. On startup, always assume empty state and force full snapshot. Use Docker restart policies.

3. **TimescaleDB deprecation trap** -- Do NOT use TimescaleDB on Supabase. It is deprecated on PG17, PG15 EOL is ~May 2026. Use native Postgres `PARTITION BY RANGE` with BRIN indexes from day one. Use `date_bin()` instead of `time_bucket()`.

4. **Supabase write throughput ceiling** -- Use direct Postgres connection (asyncpg) for collector writes, not PostgREST. Batch inserts (500-1000 rows). Disable RLS on collector-only tables. Do NOT enable Supabase Realtime on high-write tables.

5. **Stripe webhook unreliability** -- Make handlers idempotent (deduplicate by `event.id`). Never trust event ordering. Implement reconciliation cron (poll Stripe every 5-10 min). Store access as expiration timestamp, not boolean. Keep access during dunning grace period.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Database Schema + Data Collection Pipeline
**Rationale:** Everything downstream depends on having data flowing into the database. You cannot serve data you haven't collected, and you cannot collect data you have nowhere to store. This phase addresses the highest-risk pitfalls (data corruption, disconnect gaps, TimescaleDB avoidance) at the foundation.
**Delivers:** Working collector that captures L2 orderbook snapshots + deltas from Kalshi's websocket and stores them reliably in Supabase Postgres. Market discovery for automatic subscription to new markets.
**Addresses features:** Data collection pipeline, sequence number tracking, market metadata (via lifecycle channel)
**Avoids pitfalls:** Silent orderbook corruption (strict seq validation), websocket disconnection gaps (heartbeat watchdog + gap table), TimescaleDB trap (native partitioning from day one), Supabase write throughput (batched asyncpg writes)
**Stack elements:** Python 3.12, websockets, asyncpg, orjson, Supabase Postgres, tenacity (retry), structlog

### Phase 2: REST API Foundation + Auth
**Rationale:** Once data is flowing, expose it via API. Auth and rate limiting ship together because an unauthenticated API for a data product is a scraping target. The orderbook reconstruction engine is the core differentiator and belongs in the first API release.
**Delivers:** FastAPI REST API with orderbook reconstruction, raw delta queries, market metadata. API key auth with per-key rate limiting. Free tier (credit-based). OpenAPI docs auto-generated.
**Addresses features:** Historical orderbook REST API, point-in-time reconstruction, raw delta stream, market metadata endpoint, API key auth, rate limiting, free tier, OpenAPI docs, consistent error responses
**Avoids pitfalls:** Rate limiting blocking agents (token bucket + response headers + `Retry-After`), RLS performance degradation (indexes on policy columns, SELECT wrapping), data staleness not communicated (freshness metadata in responses)
**Stack elements:** FastAPI, Pydantic v2, uvicorn[standard], asyncpg (read path)

### Phase 3: Monetization + Billing
**Rationale:** Once the free tier has users, convert them to paid. Stripe integration is a distinct concern from the API itself and should not block the initial API launch. However, the access control data model (expiration-based, not boolean) must be designed in Phase 2.
**Delivers:** Stripe subscription management, tiered pricing (Free/PAYG/Project/Enterprise), usage-based metered billing, webhook handlers with idempotency, reconciliation cron. Usage dashboard for customers.
**Addresses features:** Tiered pricing, pay-as-you-go billing, usage tracking/dashboard, credit-based pricing
**Avoids pitfalls:** Stripe webhook unreliability (idempotent handlers, reconciliation cron, expiration-based access), rate limit bypass via multiple keys (user-level limiting)
**Stack elements:** Stripe SDK, Supabase Auth, APScheduler (reconciliation cron)

### Phase 4: Real-Time Websocket Streaming
**Rationale:** Requires both a working collector (data source) and a working API (auth/routing). Higher complexity than REST endpoints. Streaming is a differentiator but not a launch blocker -- historical data API validates demand first.
**Delivers:** WebSocket streaming endpoint for subscribers, fan-out architecture (collector to API server to clients), subscription management per market, backpressure handling, auth on websocket handshake.
**Addresses features:** Real-time websocket streaming, agent-friendly streaming access
**Avoids pitfalls:** Supabase Realtime as customer-facing mechanism (custom fan-out instead), connection pool exhaustion
**Stack elements:** FastAPI websocket, Redis (only if multi-instance)

### Phase 5: Agent Ecosystem + SDK
**Rationale:** Once the API is stable and documented, build the agent ecosystem. SDK and MCP server both depend on a stable OpenAPI spec. `/llms.txt` is low-effort and can ship earlier, but the SDK and MCP server need endpoint stability.
**Delivers:** Python SDK (auto-generated from OpenAPI, published to PyPI), MCP server (KalshiBook endpoints as AI agent tools), `/llms.txt` and `/llms-full.txt` discovery files, agent-friendly response refinements.
**Addresses features:** Python SDK, MCP server, `/llms.txt`, agent-friendly API design
**Stack elements:** Fern or APIMatic (SDK generation), MCP protocol

### Phase 6: Hardening + Scale
**Rationale:** Operational maturity after core product has users. Not needed for launch but needed for reliability at scale.
**Delivers:** Automated partition management (pg_cron or application), data retention policies, monitoring/alerting (gap detection, latency), connection pooling for multiple WS connections, performance optimization (materialized views, caching), flat file downloads.
**Addresses features:** Flat file downloads, enterprise tier, connection pooling/full market coverage, derived metrics
**Stack elements:** Redis (pub/sub for multi-instance), pg_cron, S3-compatible storage

### Phase Ordering Rationale

- **Data before API:** You cannot serve what you do not have. The collector must be running and storing data before any API development begins. Architecture research confirms this is a strict dependency.
- **Auth with API, not after:** An unauthenticated data API is a scraping liability. Ship rate limiting and API keys with the first API release. The security pitfalls research strongly warns against unauthenticated endpoints even on free tier.
- **Billing after API:** Monetization should not block the initial API launch. A free tier with hardcoded limits is sufficient to validate demand. Stripe integration is a distinct concern that adds complexity.
- **Streaming after REST:** Real-time streaming has higher complexity (connection management, backpressure, fan-out) and depends on both collector and API infrastructure. Historical API validates demand first.
- **Agent ecosystem after stability:** SDK and MCP server depend on stable endpoints. Building them before the API stabilizes creates maintenance burden from drift.
- **Hardening after validation:** Partition automation, monitoring, and multi-connection scaling are operational concerns that matter only after product-market fit is validated.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Data Collection):** Kalshi websocket auth uses RSA-PSS signatures with specific header format. The reconnection/re-auth pattern (every 30 min) and multi-market subscription lifecycle need careful API doc review. Sequence gap recovery is non-trivial.
- **Phase 3 (Billing):** Stripe's Meter Events API for usage-based billing is relatively new. Credit-cost-per-endpoint mapping needs design work. Dunning/grace period logic has subtle edge cases.
- **Phase 4 (Streaming):** Fan-out architecture from collector to API to clients has multiple valid patterns (in-process queue, Redis pub/sub, Supabase Broadcast). The right choice depends on whether collector and API are co-located or separate services.
- **Phase 5 (Agent Ecosystem):** MCP server implementation patterns are still emerging. SDK auto-generation tooling (Fern, APIMatic) needs evaluation.

Phases with standard patterns (can skip deep research):
- **Phase 2 (REST API + Auth):** FastAPI REST endpoints, Pydantic models, API key middleware, and rate limiting are well-documented patterns with extensive examples.
- **Phase 6 (Hardening):** Postgres partitioning, monitoring, and caching are established operational patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified against PyPI/GitHub. Architecture decisions backed by official docs (Supabase Realtime limits, TimescaleDB deprecation). Kalshi websocket format confirmed from official docs. |
| Features | MEDIUM | Based on competitor analysis (Polygon, Databento, Tardis.dev, Tavily) and domain knowledge, not user interviews. Feature prioritization is educated inference. Credit-based pricing model is proven (Tavily) but untested for this specific market. |
| Architecture | HIGH | Snapshot + delta event sourcing is the established pattern for orderbook data (Databento, Tardis.dev). Schema design verified against Kalshi API message formats. Build order driven by clear data flow dependencies. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls (sequence corruption, TimescaleDB deprecation, Supabase throughput) verified against official docs and reference implementations. Stripe webhook pitfalls from community experience. Some performance thresholds (e.g., "50-200 deltas/second") are estimates, not measured. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Kalshi websocket throughput under load:** No benchmarks exist for subscribing to 50+ markets simultaneously. The 1,000 market subscription limit is documented, but actual message throughput at scale is unknown. Test empirically in Phase 1.
- **Supabase free/pro plan write limits:** Exact write throughput ceilings for Supabase plans are not published. Batched asyncpg writes should handle MVP scale, but the ceiling is unknown. Monitor and plan for potential migration to dedicated Postgres.
- **Credit pricing model validation:** The Tavily-style credit system is a design choice, not a validated model for market data. Competitors (Polygon, Databento) use subscription tiers with rate limits, not credits. Consider A/B testing pricing models post-launch.
- **Supabase Realtime for internal transport:** The Python realtime client (`realtime-py`) is unmaintained. For Phase 4 (streaming), the internal transport from collector to API server may need Redis pub/sub or in-process queues instead of Supabase Realtime. Evaluate during Phase 4 planning.
- **MCP server patterns for financial data:** MCP is emerging and patterns are not fully standardized. Evaluate existing financial MCP servers (Polygon, Alpha Vantage) during Phase 5 planning.

## Sources

### Primary (HIGH confidence)
- [Kalshi WebSocket Connection docs](https://docs.kalshi.com/websockets/websocket-connection) -- auth, channels, heartbeat
- [Kalshi Orderbook Updates docs](https://docs.kalshi.com/websockets/orderbook-updates) -- snapshot/delta format, seq field
- [Kalshi Market Lifecycle Channel](https://docs.kalshi.com/websockets/market-&-event-lifecycle) -- market discovery
- [Supabase TimescaleDB deprecation](https://supabase.com/docs/guides/database/extensions/timescaledb) -- deprecated on PG17
- [Supabase Realtime Limits](https://supabase.com/docs/guides/realtime/limits) -- 200 connections, 100 msg/sec free plan
- [Supabase RLS Performance](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv) -- optimization patterns
- [Stripe Subscription Webhooks](https://docs.stripe.com/billing/subscriptions/webhooks) -- event lifecycle, retry behavior
- [Stripe Usage-Based Billing](https://docs.stripe.com/billing/subscriptions/usage-based) -- Meter Events API
- All PyPI version verifications (FastAPI, asyncpg, websockets, orjson, Pydantic, Stripe, uvicorn, structlog, ruff, uv)

### Secondary (MEDIUM confidence)
- [Tardis.dev](https://tardis.dev/) -- orderbook replay architecture patterns
- [Databento](https://databento.com/) -- MBO/MBP schema design reference
- [Tavily Pricing](https://www.tavily.com/pricing) -- credit-based API monetization model
- [Kalshi Go client (ammario/kalshi)](https://github.com/ammario/kalshi/blob/main/feed.go) -- reference sequence validation implementation
- [asyncpg vs psycopg3 benchmarks](https://fernandoarteaga.dev/blog/psycopg-vs-asyncpg/) -- performance comparison
- [Supabase Batch Insert Best Practices](https://github.com/orgs/supabase/discussions/11349) -- community patterns

### Tertiary (LOW confidence)
- [Hacker News: FastAPI + Supabase](https://news.ycombinator.com/item?id=42353177) -- community integration patterns
- [FinFeedAPI](https://www.finfeedapi.com/) -- prediction market API competitor (403 blocked, limited info)
- Supabase write throughput limits -- not published, estimated from community reports

---
*Research completed: 2026-02-13*
*Ready for roadmap: yes*
