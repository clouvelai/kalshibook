# Phase 4: Backtesting-Ready API - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete the data API layer so customers can build their own backtesting frameworks on top of it. This means filling gaps in the current API: capturing public trades, normalizing settlement data, serving candlestick/OHLC data, and exposing event/market hierarchy. The collector must be extended to capture trade executions alongside orderbook data.

**Not in scope:** Live real-time streaming (future milestone — performance guarantees and 1k market limit unresolved). Agent-first SDK (ships with backtesting framework in next milestone). Historical backfill for pre-collection markets.

</domain>

<decisions>
## Implementation Decisions

### Public trade capture
- Add `trades` WS channel subscription to the collector — capture all public trade executions
- Store trade data: timestamp, price, quantity, side, market ticker
- Serve trade history via API endpoint with time range + market filtering
- This is essential — backtesters need real execution data, not just simulated fills from orderbook state

### Settlement data
- Normalize settlement/resolution data into a proper queryable format (not buried in JSONB metadata)
- Reference Kalshi's `/settlements` REST endpoint for data model
- Backtesters need clean resolution data for P&L calculation: market ticker, outcome, settlement time

### Candlestick/OHLC data
- Serve candlestick data at 1-minute, 1-hour, and 1-day intervals
- Candles include OHLC for bid/ask, trade prices, volume, and open interest
- Enables strategy-level backtesting (directional/momentum) for customers who don't need full L2 orderbook replay

### Event/market hierarchy
- Expose the Series > Event > Market structure where series exists
- Event > Market relationship for events without a series
- Backtesters often need all markets within an event (e.g., all strike prices for "Bitcoin > $X")

### Data scope
- Forward data only — no historical backfill for markets that existed before collection started
- Will start fresh when deploying to production

### Claude's Discretion
- Candle data packaging: whether candles are a separate endpoint tier or bundled with existing data (same credit system)
- Whether to compute candles from raw orderbook/trade data vs. proxy from Kalshi's REST API
- API design patterns for new endpoints (follow Phase 2 conventions)
- Credit costs for new endpoints (trades, settlements, candles)
- Collector implementation details for trades WS subscription

</decisions>

<specifics>
## Specific Ideas

- "Customers should be able to build their own backtesting frameworks if they wanted to" — the API layer must be complete enough for this
- Tavily (tavily.com) referenced as model for agent-first SDK design — applies to next milestone, not this one
- "The complete orderbook isn't easily accessible or curated by amateurs" — this is the core value proposition
- Candle-only data enables a different tier of backtesting (directional strategies) vs. L2 orderbook (execution-level strategies like market-making)

</specifics>

<deferred>
## Deferred Ideas

- **Real-time streaming (live orderbook updates via websocket)** — Future milestone. Requires performance guarantees and solving the 1,000 market subscription limit.
- **Agent-first SDK/client library (Tavily-style)** — Next milestone, ships alongside the backtesting framework.
- **Historical backfill** — Fetching historical trades/candles for markets that existed before collection started. Future consideration.
- **Bulk data access** — Streaming downloads, efficient bulk export for large datasets. Can revisit.
- **Multi-market query optimization** — Cross-market queries, batch endpoints. Can revisit.
- **First-party backtesting framework** — "Beautiful, seamless, agent-first backtesting system" built on top of the data layer. Next milestone.

</deferred>

---

*Phase: 04-backtesting-ready-api*
*Context gathered: 2026-02-15*
