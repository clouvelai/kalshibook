---
phase: 04-backtesting-ready-api
plan: 02
subsystem: collector
tags: [websocket, rest-api, trades, settlements, enrichment, httpx, rsa-pss, asyncio]

# Dependency graph
requires:
  - phase: 04-backtesting-ready-api
    plan: 01
    provides: "trades, settlements, events, series tables and partition management"
provides:
  - "TradeExecution and SettlementData dataclasses for WS/REST data capture"
  - "KalshiRestClient with RSA-PSS auth for market/event/series REST enrichment"
  - "Trade channel subscription capturing all public trade executions"
  - "Fire-and-forget enrichment pipeline (settlement + event/series metadata)"
  - "Trade and settlement writer buffers with partition management"
  - "Event and series direct upsert methods in writer"
affects: [04-03-trade-settlement-endpoints, 04-04-candle-hierarchy-endpoints]

# Tech tracking
tech-stack:
  added: [httpx (async REST client for enrichment)]
  patterns:
    - "Fire-and-forget asyncio tasks with GC protection set for non-blocking enrichment"
    - "RSA-PSS REST auth headers matching WS auth pattern (shared key/algorithm)"
    - "Settlement retry on empty result (5s delay for API propagation race condition)"
    - "On-demand trade partition creation mirroring delta partition pattern"

key-files:
  created:
    - src/collector/enrichment.py
  modified:
    - src/collector/models.py
    - src/collector/writer.py
    - src/collector/main.py
    - src/collector/discovery.py
    - src/shared/config.py

key-decisions:
  - "Enrichment calls are async fire-and-forget to avoid blocking the WS message loop"
  - "Settlement enrichment retries once after 5s on empty result (Kalshi API propagation delay)"
  - "Trade channel subscribed without market_tickers filter (receives ALL public trades)"
  - "Event/series writes are direct upserts (no buffering) since they are low-volume"

patterns-established:
  - "Fire-and-forget task pattern with self._fire_and_forget set for GC protection"
  - "REST API authentication reuses same RSA-PSS key/algo as WS auth"
  - "on_enrichment_needed callback pattern extending discovery callbacks"

# Metrics
duration: 4min
completed: 2026-02-15
---

# Phase 4 Plan 2: Collector Extension Summary

**Trade capture via WS subscription, settlement enrichment via Kalshi REST API with RSA-PSS auth, and event/series hierarchy metadata collection**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-15T21:00:41Z
- **Completed:** 2026-02-15T21:04:50Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- TradeExecution and SettlementData frozen dataclasses with trade/settlement writer buffers and on-demand partition management
- KalshiRestClient with RSA-PSS authentication matching the WS auth pattern, with get_market/get_event/get_series endpoints
- Collector subscribes to trade WS channel (all markets), parses trades, and buffers to DB
- Lifecycle events trigger fire-and-forget REST enrichment for settlement data and event/series hierarchy metadata
- Settlement enrichment retries once on empty result to handle Kalshi API propagation delay
- Event/series upsert methods in writer for low-volume direct DB writes

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TradeExecution model and extend writer with trade/settlement buffers** - `9e2db56` (feat)
2. **Task 2: Create Kalshi REST enrichment client and wire collector** - `f09b2c2` (feat)

## Files Created/Modified
- `src/collector/enrichment.py` - KalshiRestClient with RSA-PSS auth for market/event/series REST endpoints
- `src/collector/models.py` - TradeExecution and SettlementData frozen dataclasses
- `src/collector/writer.py` - Trade/settlement buffers, flush methods, partition management, event/series upserts
- `src/collector/main.py` - Trade message handling, enrichment wiring, fire-and-forget task management
- `src/collector/discovery.py` - on_enrichment_needed callback for lifecycle events
- `src/shared/config.py` - kalshi_rest_base_url setting

## Decisions Made
- Enrichment calls are async fire-and-forget to avoid blocking the WS message loop (same pattern as billing fire-and-forget in deps.py)
- Settlement enrichment retries once after 5s on empty result (Kalshi API propagation race condition)
- Trade channel subscribed without market_tickers filter to receive ALL public trades
- Event/series are low-volume direct upserts (no buffering needed unlike trades/deltas)
- REST auth signs `timestamp + METHOD + path` matching WS auth algorithm but with REST-specific path format

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Existing Kalshi API credentials (key_id + private_key) are reused for REST auth.

## Next Phase Readiness
- All data capture paths active: orderbook (existing) + trades + settlements + events/series
- Trade and settlement data flowing to DB tables created in Plan 01
- Ready for API endpoint implementation (Plans 03-04) to expose this data
- Enrichment client can be extended for additional REST endpoints if needed

## Self-Check: PASSED

All 6 files verified present. Both task commits (`9e2db56`, `f09b2c2`) confirmed in git log.

---
*Phase: 04-backtesting-ready-api*
*Completed: 2026-02-15*
