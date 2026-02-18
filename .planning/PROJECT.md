# KalshiBook

## What This Is

A monetized data API that collects, stores, and serves L2 orderbook data from Kalshi prediction markets. Customers (algo traders, quants, and AI agents) query historical point-in-time orderbook state, access trade/settlement/candle data for backtesting, discover market coverage, and manage their accounts through a self-service dashboard. Tavily-style API with free tier through project plans.

## Core Value

Reliable, complete orderbook history for every Kalshi market — reconstructable to any point in time. If customers can't trust the data is complete and accurate, nothing else matters.

## Requirements

### Validated

- ✓ Collect L2 orderbook snapshots + deltas via Kalshi websocket API — v1.0
- ✓ Auto-discover new markets via market/event lifecycle websocket — v1.0
- ✓ Store all raw snapshots and deltas in Supabase with timestamps — v1.0
- ✓ Reconstruct full orderbook state at any historical timestamp — v1.0
- ✓ Serve reconstructed orderbook via REST API — v1.0
- ✓ Serve raw delta streams for advanced users — v1.0
- ✓ API key authentication with subscription tiers (free / PAYG / project) — v1.0
- ✓ Stripe-powered billing and subscription management — v1.0
- ✓ User dashboard for API key management, usage tracking, billing — v1.0
- ✓ Agent-friendly API design (structured JSON, clean endpoints, documentation) — v1.0
- ✓ Market metadata (event info, contract specs, settlement rules) — v1.0
- ✓ Trade capture and history queryable via API — v1.0
- ✓ Candlestick data at 1m/1h/1d intervals — v1.0
- ✓ Interactive API playground — v1.0
- ✓ Python SDK published to PyPI as installable package — v1.1
- ✓ SDK reference documentation (mkdocs-material with auto-generated API reference) — v1.1
- ✓ Data discovery helpers in SDK (list available markets, coverage dates) — v1.1
- ✓ Typed response models and exception hierarchy — v1.1
- ✓ Sync and async client with auto-pagination and DataFrame support — v1.1
- ✓ Market coverage visibility (browsable, searchable coverage with segment detection) — v1.2
- ✓ Playground with real captured market tickers and zero-credit demos — v1.2
- ✓ Canvas depth chart visualization in playground — v1.2

### Active

- [ ] Pricing validation against real data volumes
- [ ] Animated orderbook replay with play/pause/scrub controls
- [ ] SDK backtesting abstractions (replay_orderbook, stream_trades)

### Future

- [ ] Credit budget parameter for large SDK queries
- [ ] Stream real-time orderbook updates to subscribers via websocket
- [ ] Real-time streaming requires valid API key authentication on connect
- [ ] TypeScript SDK auto-generated from OpenAPI spec
- [ ] MCP server exposing KalshiBook endpoints as AI agent tools
- [ ] Downloadable flat files (CSV/Parquet) for bulk backtesting
- [ ] Public landing page with marketing-ready demo
- [ ] Calendar heatmap for data density visualization
- [ ] Coverage page accessible publicly (marketing value)

### Out of Scope

- Trade execution / order placement — read-only data product, not a brokerage
- Multi-exchange aggregation (Polymarket, Manifold) — deep on Kalshi first
- GraphQL API — REST-only, better for agents, simpler to rate-limit
- Mobile app — web dashboard + API only
- Derived metrics (spread, mid-price, order imbalance) — users compute from raw data

## Context

**Domain**: Kalshi is a CFTC-regulated prediction market exchange. Markets are event contracts (binary outcomes) with continuous orderbooks. The websocket API provides L2 orderbook data: initial snapshot on subscribe, then incremental deltas.

**Market universe**: More active markets than a single websocket connection supports (1k subscription limit). MVP uses single connection subscribing to liquid/popular markets. Future milestones add connection pooling to cover full universe.

**Data model**: Each market's orderbook state is reconstructable from an initial snapshot plus ordered sequence of deltas. Store both raw for replay fidelity.

**Customer persona**: Algo traders and AI agents (e.g., Claude, GPT-based trading bots) building automated strategies on Kalshi. They need:
- Historical orderbook state for backtesting
- Real-time feeds for live strategy execution
- Programmatic access (API-first, not dashboards)

**Current state (v1.2 shipped):**
- Backend: Python/FastAPI, 6,313 LOC — 10 data endpoints + coverage + playground endpoints, credit billing, Supabase Auth
- Frontend: Next.js 15/TypeScript, 7,519 LOC — dashboard with key management, billing, playground, coverage page, depth chart
- SDK: Python/httpx, 1,630 LOC — typed client with sync/async, 20 endpoint methods, auto-pagination, DataFrame support
- Docs: mkdocs-material site with Getting Started, Authentication, endpoint examples, auto-generated API reference
- Infrastructure: Supabase (Postgres), Stripe, Railway (collector), PyPI (kalshibook package)
- Data: daily-partitioned tables for snapshots, deltas, trades; settlements, events, series; materialized coverage view

## Constraints

- **Datastore**: Supabase (managed Postgres) — PostgREST for admin, custom FastAPI for customer-facing
- **Billing**: Stripe for payments and subscription management
- **Collector hosting**: Railway (long-running websocket process)
- **Kalshi WS limit**: 1,000 market subscriptions per websocket connection (MVP: single connection)
- **Data source**: Kalshi websocket API requires authentication (API key from Kalshi account)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase as primary datastore | Managed Postgres + built-in Auth reduces custom code | ✓ Good — Auth and Postgres work well, PostgREST unused for customer API |
| Stripe for billing | Industry standard, good API, subscription management built-in | ✓ Good — Checkout, Portal, Webhooks, Metering all working |
| Railway for collector | Needs long-running process, Railway handles persistent services | ✓ Good |
| Single WS connection for MVP | Simplifies architecture, covers liquid markets | ✓ Good — pooling deferred to v2 |
| Tavily-style pricing model | Free tier for adoption, usage-based scaling | ✓ Good — 3 tiers working |
| Agent-first API design | AI agents are growing customer segment for market data | ✓ Good — llms.txt, structured errors |
| Custom FastAPI over PostgREST | Reconstruction + credit metering need app logic | ✓ Good — 10 endpoints with custom business logic |
| Custom WS server over Supabase Realtime | Python client unmaintained, 8KB NOTIFY limit | — Pending (v2 streaming) |
| Native Postgres partitioning over TimescaleDB | TimescaleDB deprecated on Supabase PG17 | ✓ Good — daily partitions working |
| httpx GoTrue client over supabase-py | websockets>=16 conflict, cleaner direct REST | ✓ Good — no dependency conflicts |
| Two-step orderbook reconstruction | Snapshot + delta replay clearer than single CTE | ✓ Good — debuggable and correct |
| Credit system as primary rate enforcement | SlowAPI backstop only, credits are real limiter | ✓ Good — simple and effective |

## Key Decisions (v1.1)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hand-written SDK over code generation | Better ergonomics for 10 endpoints; abstractions can't be generated | ✓ Good — clean typed API |
| httpx + stdlib dataclasses (no Pydantic) | Avoids version conflicts with consumer projects | ✓ Good — zero conflicts |
| Single KalshiBook class with sync=True flag | Simpler than separate AsyncKalshiBook class | ✓ Good — one import |
| Replay abstractions deferred to v1.2 | Ship SDK core first, add high-level abstractions later | ✓ Good — v1.1 shipped faster |
| uv_build backend with src layout | Zero-config package discovery in monorepo | ✓ Good |
| PageIterator with eager first-page fetch | Errors surface at call time, not during iteration | ✓ Good — better DX |
| mkdocs-material with gen-files/literate-nav | Auto-generated API reference from NumPy docstrings | ✓ Good |

## Key Decisions (v1.2)

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Materialized view for coverage stats | Live partition scans too slow at scale | ✓ Good — fast coverage queries |
| Gaps-and-islands SQL for segment detection | Avoids false single-range reporting on gapped data | ✓ Good — accurate segments |
| Advisory lock on matview refresh | Prevents concurrent refresh conflicts without blocking reads | ✓ Good |
| Event-level pagination (not market-level) | Dashboard shows events as groups | ✓ Good — natural grouping |
| Canvas over SVG for depth chart | Future animation support, no rewrite path from SVG | ✓ Good — ~250 lines, zero bundle impact |
| Zero-credit playground demos | Dashboard-internal endpoint skips billing | ✓ Good — frictionless exploration |
| No charting library for depth chart | Raw Canvas 2D sufficient, zero bundle impact | ✓ Good |
| Replay animation deferred to v1.3 | Ship static depth chart first, validate demand | ✓ Good — shipped faster |

---
*Last updated: 2026-02-18 after v1.2 milestone*
