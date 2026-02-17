# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-13)

**Core value:** Reliable, complete orderbook history for every Kalshi market -- reconstructable to any point in time
**Current focus:** Phase 7 COMPLETE -- V1 Cleanup & Polish (plan 1 of 1 done)

## Current Position

Phase: 7 of 7 (V1 Cleanup & Polish)
Plan: 1 of 1 in current phase
Status: 07-01 complete -- Timestamp validation, dead code removal, requirements traceability
Last activity: 2026-02-17 - Completed 07-01: V1 cleanup & polish

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 17
- Average duration: 3min
- Total execution time: 0.81 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3 | 12min | 4min |
| 03 | 2 | 5min | 2.5min |
| 04 | 4 | 11min | 2.75min |
| 05 | 4 | 12min | 3min |
| 06 | 3 | 7min | 2.3min |
| 07 | 1 | 3min | 3min |

**Recent Trend:**
- Last 5 plans: 3min, 3min, 2min, 2min, 3min
- Trend: stable

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
- [03-review]: Stripe API calls wrapped in try/except for 502 error responses (not silent 500s)
- [03-review]: CHECK (credits_used >= 0) added as DB-level guard on billing_accounts
- [03-review]: asyncio.create_task references stored in set to prevent GC killing fire-and-forget tasks
- [03-review]: deduct_credits RETURNING includes stripe_customer_id (eliminated redundant query)
- [03-review]: _to_uuid helper extracted, duplicate Stripe customer creation deduplicated
- [03-review]: No billing-specific tests yet — add when Phase 4/5 test infrastructure is built
- [04-01]: Trades table mirrors deltas partitioning strategy (daily PARTITION BY RANGE on ts)
- [04-01]: Settlements denormalized (no FK to markets) for write performance and direct query access
- [04-01]: Events/series tables are independent (no FKs) -- hierarchy is conceptual via ticker references
- [04-03]: Trades endpoint uses exclusive end time (ts < end) for clean time-range semantics
- [04-03]: Settlements list uses dynamic query building for optional filters (event_ticker, result)
- [04-02]: Enrichment calls are async fire-and-forget to avoid blocking WS message loop
- [04-02]: Settlement enrichment retries once after 5s on empty result (Kalshi API propagation delay)
- [04-02]: Trade channel subscribed without market_tickers filter (receives ALL public trades)
- [04-02]: Event/series are low-volume direct upserts (no buffering needed unlike trades/deltas)
- [04-04]: Candle OHLCV uses array_agg for open/close (first/last trade) and MAX/MIN for high/low
- [04-04]: Empty candle buckets omitted (no forward-fill server-side); documented for consumers
- [04-04]: Events endpoint uses correlated subquery for market_count (acceptable at current scale)
- [05-01]: key_type column is cosmetic only (dev/prod labels, no rate limit differences) -- easy to extend later
- [05-01]: Signup provisioning wrapped in try/except so auth never fails due to provisioning errors
- [05-01]: Usage aggregation scoped to billing_cycle_start via subquery (not hardcoded month boundary)
- [05-01]: Google OAuth users use lazy init pattern (dashboard creates default key on first load)
- [05-02]: Signup flow calls FastAPI first (provisions billing + key) then Supabase signInWithPassword for browser session
- [05-02]: API proxy via Next.js rewrites eliminates CORS -- no backend CORS config needed
- [05-02]: shadcn/ui sonner replaces deprecated toast component
- [05-02]: LoginForm wrapped in Suspense for useSearchParams SSR compatibility in Next.js 15
- [05-03]: Dashboard layout uses server component for auth + client DashboardShell wrapper for SidebarProvider
- [05-03]: Documentation sidebar link opens /api/llms-full.txt in new tab (proxied via Next.js rewrites)
- [05-03→quick-1]: Overview keys table now has inline quick actions (copy prefix, edit name/type, revoke) via icon buttons
- [05-03]: Mobile sidebar uses SidebarTrigger in a sticky header bar
- [05-04]: Show-once key pattern: raw key in React state only during dialog Phase 2, cleared on close
- [05-04]: Suspense boundary for BillingPageContent useSearchParams (same pattern as LoginForm)
- [05-04]: Stripe portal button disabled for free tier without PAYG (no Stripe customer)
- [05-04]: Added shadcn Select component for key type dev/prod dropdown
- [06-01]: Playground fetch uses API key auth (not Supabase JWT) to mirror real API usage
- [06-01]: Auto-reveal first API key on mount for zero-friction playground experience
- [06-01]: Curl generation masks key after first 10 prefix chars for security display
- [06-02]: CodeBlock uses prism-react-renderer vsDark theme with bash language for curl display
- [06-02]: Disabled Python/JS tabs use shadcn Tooltip with Coming soon message
- [06-02]: Response tab shows temporary CodeBlock JSON display (Plan 03 adds full ResponsePanel)
- [06-03]: ResponsePanel uses three-state pattern (empty/loading/response) -- error responses are regular response objects with non-2xx status
- [06-03]: OrderbookPreview uses runtime type guard to detect orderbook format and falls back gracefully
- [06-03]: Status badge uses destructive variant for non-2xx, secondary for 2xx
- [07-01]: Timestamp promoted to top-level visible field (not in accordion) matching Market Ticker pattern
- [07-01]: requestError rendered below form inside left panel for visual proximity to form inputs

### Pending Todos

1. ~~**Hydrate market metadata via REST API on discovery** (collector)~~ — Partially addressed by 04-02 enrichment client (event/series metadata on discovery). Full market metadata hydration (open_time etc.) can use same KalshiRestClient.
2. **Subscribe to ticker WS channel for open interest data** (collector) — The Kalshi `ticker` channel provides open interest that we can't derive from trades/orderbook. Would enrich candle data. Low priority — trade-price candles + volume serve primary use case.
3. **Fetch Kalshi event candlesticks for untracked markets** (api) — Kalshi's public GET /series/{series}/events/{event}/candlesticks returns rich OHLC+volume+OI data for ALL markets in an event, no auth needed. Would enable directional backtesting for events we don't track.

### Roadmap Evolution

- Phase 6 added: API Playground
- Phase 7 added: V1 Cleanup & Polish (gap closure from milestone audit)

### Blockers/Concerns

- None active. supabase-py websockets conflict resolved by building httpx GoTrue client (02-03).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Add inline quick actions (copy, edit, delete) to overview API keys table | 2026-02-16 | b9cad55 | [1-implement-the-quick-actions-on-the-api-p](./quick/1-implement-the-quick-actions-on-the-api-p/) |

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 07-01-PLAN.md (final plan of phase 7 -- v1 cleanup complete)
Resume file: .planning/phases/07-v1-cleanup-polish/07-01-SUMMARY.md
