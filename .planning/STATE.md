# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-13)

**Core value:** Reliable, complete orderbook history for every Kalshi market -- reconstructable to any point in time
**Current focus:** Phase 2 - REST API + Authentication

## Current Position

Phase: 2 of 5 (REST API + Authentication)
Plan: 2 of 3 in current phase
Status: Executing
Last activity: 2026-02-14 -- Completed 02-02 (Data Endpoints)

Progress: [████░░░░░░] 36%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 3.5min
- Total execution time: 0.12 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 2 | 7min | 3.5min |

**Recent Trend:**
- Last 5 plans: 5min, 2min
- Trend: improving

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Custom FastAPI for all customer-facing endpoints, not Supabase PostgREST (reconstruction + metering need app logic)
- [Roadmap]: Custom websocket server for subscriber feeds, not Supabase Realtime (Python client unmaintained, 8KB NOTIFY limit)
- [Roadmap]: Native Postgres partitioning, not TimescaleDB (deprecated on Supabase PG17)
- [02-01]: Deferred supabase-py install due to websockets>=16 conflict; resolve in Plan 02-03
- [02-01]: Decoupled shared/db.py from collector.metrics using structlog directly
- [02-01]: Stub route files for Plans 02/03 rather than conditional imports
- [02-02]: Two-step reconstruction (snapshot + deltas) over single CTE for clarity and debuggability
- [02-02]: Cursor pagination with orjson-encoded base64 (ts, id) composite cursor
- [02-02]: Correlated subqueries for market coverage dates (acceptable at MVP scale)

### Pending Todos

1. **Hydrate market metadata via REST API on discovery** (collector) — When joining a market mid-stream, fetch open_time/metadata from Kalshi REST API so we know how late we are. Fits Phase 2.

### Blockers/Concerns

- supabase-py requires websockets<16 but project uses websockets>=16.0 (Kalshi WS collector). Must resolve for Plan 02-03 auth proxy endpoints.

## Session Continuity

Last session: 2026-02-14
Stopped at: Completed 02-02-PLAN.md (Data Endpoints)
Resume file: .planning/phases/02-rest-api-authentication/02-02-SUMMARY.md
