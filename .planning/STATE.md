# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** Reliable, complete orderbook history for every Kalshi market -- reconstructable to any point in time
**Current focus:** Phase 10 - Client Class Data Endpoints (v1.1 Python SDK)

## Current Position

Phase: 10 of 12 (Client Class Data Endpoints)
Plan: 1 of 2 in current phase (10-01 complete)
Status: In Progress
Last activity: 2026-02-17 -- Plan 10-01 (Client Endpoint Methods) complete

Progress: [##########################....] 80% (9/12 phases, 24 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 24
- Average duration: 3min
- Total execution time: ~1.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 1 | ~3min | 3min |
| 02 | 3 | 12min | 4min |
| 03 | 2 | 5min | 2.5min |
| 04 | 4 | 11min | 2.75min |
| 05 | 5 | 12min | 2.4min |
| 06 | 3 | 7min | 2.3min |
| 07 | 1 | 3min | 3min |
| 08 | 1 | 2min | 2min |
| 09 | 3 | 5min | 1.7min |
| 10 | 1 | 1min | 1min |

**Recent Trend:**
- Last 5 plans: 2min, 1min, 2min, 2min, 1min
- Trend: Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table with outcomes.

v1.1 decisions:
- Hand-written SDK over code generation (research consensus, 3 of 4 files reject generation)
- httpx + stdlib dataclasses (no Pydantic in SDK -- avoids version conflicts)
- Single KalshiBook class with sync=True flag (not separate AsyncKalshiBook)
- Replay abstractions (replay_orderbook, stream_trades) deferred to v1.2
- Root project renamed to kalshibook-server to avoid uv workspace name collision
- SDK uses uv_build backend with src layout for zero-config package discovery
- httpx>=0.27 as sole runtime dependency (no upper bound); pandas>=2.0 as optional extra
- SDK exceptions use status_code/response_body attributes (distinct from server's code/status pattern)
- parse_datetime normalizes Z suffix to +00:00 for Python 3.10 compatibility
- Flat dataclass structures (no inheritance) for MarketDetail/EventDetail -- stdlib slots+inheritance broken
- ResponseMeta.from_headers() uses -1 sentinel for missing credit headers (not 0, which is valid)
- Local _VERSION constant in _http.py to avoid circular import (Phase 12 refactors to single source)
- Retry-After header honored when present on 429, exponential backoff with jitter as fallback
- No client-side interval validation for get_candles -- server validates for forward-compatibility
- _ensure_tz defensively handles naive datetimes for outbound serialization (mirrors _parsing.py pattern)

### Pending Todos

1. **Subscribe to ticker WS channel for open interest data** (collector)
2. **Fetch Kalshi event candlesticks for untracked markets** (api)
3. **Pre-populate playground with real captured market data** (dashboard)

### Blockers/Concerns

- None active.

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 10-01-PLAN.md
Resume: Continue with 10-02-PLAN.md (paginated endpoint methods)
