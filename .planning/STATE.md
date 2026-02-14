# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-13)

**Core value:** Reliable, complete orderbook history for every Kalshi market -- reconstructable to any point in time
**Current focus:** Phase 3 complete -- ready for Phase 4

## Current Position

Phase: 3 of 5 (Billing + Monetization) -- COMPLETE
Plan: 2 of 2 in current phase (all plans complete)
Status: Phase Complete
Last activity: 2026-02-14 -- Completed 03-02 (Stripe billing routes, webhooks, AI discovery docs)

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 3min
- Total execution time: 0.28 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3 | 12min | 4min |
| 03 | 2 | 5min | 2.5min |

**Recent Trend:**
- Last 5 plans: 2min, 5min, 3min, 2min
- Trend: stable/improving

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
- [02-03]: Used httpx directly against Supabase GoTrue REST API instead of supabase-py (websockets conflict resolved permanently)
- [02-03]: Separated JWT auth (key management) from API key auth (data endpoints) via distinct dependencies
- [02-03]: llms-full.txt at 515 lines covers full auth flow, all endpoints, error codes, backtesting workflow
- [03-01]: Rate limiter set to 120/minute backstop; credit system is real enforcement (avoids SlowAPI tier-awareness complexity)
- [03-01]: Billing accounts created lazily on first API request via upsert (not at signup)
- [03-01]: PAYG overage and usage logging use asyncio.create_task fire-and-forget to avoid blocking request path
- [03-02]: Billing endpoints use Supabase JWT auth (not API keys) since they manage account-level state
- [03-02]: Webhook handlers are idempotent; payment failures logged only (Stripe retries before sending subscription.deleted)
- [03-02]: PAYG toggle auto-creates Stripe customer to reduce friction

### Pending Todos

1. **Hydrate market metadata via REST API on discovery** (collector) — When joining a market mid-stream, fetch open_time/metadata from Kalshi REST API so we know how late we are. Fits Phase 2.

### Blockers/Concerns

- None active. supabase-py websockets conflict resolved by building httpx GoTrue client (02-03).

## Session Continuity

Last session: 2026-02-14
Stopped at: Completed 03-02-PLAN.md (Stripe billing routes + AI discovery docs) -- Phase 3 complete
Resume file: None
