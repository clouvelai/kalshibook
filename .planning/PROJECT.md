# KalshiBook

## What This Is

A monetized data API that collects, stores, and serves L2 orderbook data from Kalshi prediction markets. Customers (algo traders, quants, and AI agents) query historical point-in-time orderbook state, access trade/settlement/candle data for backtesting, and manage their accounts through a self-service dashboard. Tavily-style API with free tier through project plans.

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

### Active

- [ ] Python SDK with high-level backtesting abstractions (replay_orderbook, stream_trades)
- [ ] SDK published to PyPI as installable package
- [ ] SDK reference documentation (pdoc or similar)
- [ ] Data discovery helpers in SDK (list available markets, coverage dates)

### Future

- [ ] Stream real-time orderbook updates to subscribers via websocket
- [ ] Real-time streaming requires valid API key authentication on connect
- [ ] TypeScript SDK auto-generated from OpenAPI spec
- [ ] MCP server exposing KalshiBook endpoints as AI agent tools
- [ ] Downloadable flat files (CSV/Parquet) for bulk backtesting

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

**Current state (v1.0 shipped):**
- Backend: Python/FastAPI, 6,346 LOC — 10 data endpoints, credit billing, Supabase Auth
- Frontend: Next.js 15/TypeScript, 5,684 LOC — dashboard with key management, billing, playground
- Infrastructure: Supabase (Postgres), Stripe, Railway (collector)
- Data: daily-partitioned tables for snapshots, deltas, trades; settlements, events, series

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

## Current Milestone: v1.1 Python SDK

**Goal:** Give users a first-class Python client for backtesting — install via pip, replay orderbooks, stream trades, discover available data.

**Target features:**
- Auto-generated Python SDK wrapping all REST endpoints
- High-level backtesting abstractions (orderbook replay, trade streaming)
- Data discovery helpers (available markets, coverage dates)
- SDK reference docs

---
*Last updated: 2026-02-17 after v1.1 milestone start*
