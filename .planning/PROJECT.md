# KalshiBook

## What This Is

A monetized data API that collects, stores, and serves L2 orderbook data from Kalshi prediction markets. Customers (algo traders, quants, and AI agents) query historical point-in-time orderbook state, stream real-time updates, and access raw deltas for backtesting and live trading strategies. Tavily-style API with free tier through enterprise plans.

## Core Value

Reliable, complete orderbook history for every Kalshi market — reconstructable to any point in time. If customers can't trust the data is complete and accurate, nothing else matters.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Collect L2 orderbook snapshots + deltas via Kalshi websocket API
- [ ] Auto-discover new markets via market/event lifecycle websocket
- [ ] Store all raw snapshots and deltas in Supabase with timestamps
- [ ] Reconstruct full orderbook state at any historical timestamp
- [ ] Serve reconstructed orderbook via REST API
- [ ] Stream real-time orderbook updates to subscribers via websocket
- [ ] Serve raw delta streams for advanced users
- [ ] API key authentication with subscription tiers (free / pay-as-you-go / project / enterprise)
- [ ] Stripe-powered billing and subscription management
- [ ] User dashboard for API key management, usage tracking, billing
- [ ] Agent-friendly API design (structured JSON, clean endpoints, documentation)
- [ ] Market metadata (event info, contract specs, settlement rules)

### Out of Scope

- Connection pooling / multi-WS redundancy — future milestone, single WS connection for MVP
- Consensus + reconciliation across redundant listeners — future milestone
- OHLCV-style aggregated candle data — may add later based on demand
- Mobile app — web dashboard only
- Trade execution API — read-only data, no trading

## Context

**Domain**: Kalshi is a CFTC-regulated prediction market exchange. Markets are event contracts (binary outcomes) with continuous orderbooks. The websocket API provides L2 orderbook data: initial snapshot on subscribe, then incremental deltas.

**Market universe**: More active markets than a single websocket connection supports (1k subscription limit). MVP uses single connection subscribing to liquid/popular markets. Future milestones add connection pooling to cover full universe.

**Data model**: Each market's orderbook state is reconstructable from an initial snapshot plus ordered sequence of deltas. Store both raw for replay fidelity.

**Customer persona**: Algo traders and AI agents (e.g., Claude, GPT-based trading bots) building automated strategies on Kalshi. They need:
- Historical orderbook state for backtesting
- Real-time feeds for live strategy execution
- Programmatic access (API-first, not dashboards)

**Reference product**: Tavily (tavily.com) — clean API design, simple pricing tiers, agent-first positioning. KalshiBook should feel similarly natural for an AI agent to integrate with.

**Existing codebase**: Python project with FastAPI/Starlette patterns, pytest test suite, modern tooling (pyproject.toml, uv). See `.planning/codebase/` for detailed mapping.

## Constraints

- **Datastore**: Supabase (managed Postgres) — leverage PostgREST, Realtime, Auth, RLS where possible
- **Billing**: Stripe for payments and subscription management
- **Collector hosting**: Railway (long-running websocket process)
- **Kalshi WS limit**: 1,000 market subscriptions per websocket connection (MVP: single connection)
- **Data source**: Kalshi websocket API requires authentication (API key from Kalshi account)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supabase as primary datastore | Managed Postgres + built-in API/Auth/Realtime reduces custom code | — Pending |
| Stripe for billing | Industry standard, good API, subscription management built-in | — Pending |
| Railway for collector | Needs long-running process, Railway handles persistent services well | — Pending |
| Single WS connection for MVP | Simplifies architecture, covers liquid markets, pooling comes later | — Pending |
| Tavily-style pricing model | Free tier for adoption, usage-based scaling, agent-friendly | — Pending |
| Agent-first API design | Key differentiator — AI agents are a growing customer segment for market data | — Pending |

---
*Last updated: 2026-02-13 after initialization*
