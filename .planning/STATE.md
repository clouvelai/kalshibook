# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** Reliable, complete orderbook history for every Kalshi market -- reconstructable to any point in time
**Current focus:** Phase 12 - Documentation & PyPI Publishing (v1.1 Python SDK)

## Current Position

Phase: 12 of 12 (Documentation & PyPI Publishing)
Plan: 1 of 3 in current phase (12-01 complete)
Status: Executing Phase 12
Last activity: 2026-02-17 -- Plan 12-01 (Docs Infrastructure & Version Fix) complete

Progress: [#############################.] 93% (12/12 phases, 28 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 28
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
| 10 | 2 | 3min | 1.5min |
| 11 | 2 | 4min | 2min |
| 12 | 1 | 2min | 2min |

**Recent Trend:**
- Last 5 plans: 2min, 1min, 2min, 2min, 2min
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
- _version.py module as single version source replacing _VERSION constant in _http.py (resolved Phase 12)
- Retry-After header honored when present on 429, exponential backoff with jitter as fallback
- No client-side interval validation for get_candles -- server validates for forward-compatibility
- _ensure_tz defensively handles naive datetimes for outbound serialization (mirrors _parsing.py pattern)
- pytest-httpx match_params for query-parameterized endpoint URL matching (exact URL match fails with query strings)
- PageIterator tracks all yielded items in _consumed list so to_df() always returns complete dataset
- to_df() drains remaining pages via list(self) before converting -- ensures completeness even after partial iteration
- Eager first-page fetch in paginated methods so errors surface at call time, not during iteration
- Inner closure pattern for fetch_page captures pre-computed ISO timestamps outside the closure
- mkdocs-material with gen-files/literate-nav recipe for auto-generated API reference from NumPy docstrings

### Pending Todos

1. **Subscribe to ticker WS channel for open interest data** (collector)
2. **Fetch Kalshi event candlesticks for untracked markets** (api)
3. **Pre-populate playground with real captured market data** (dashboard)

### Blockers/Concerns

- None active.

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 12-01-PLAN.md
Resume: Continue with Plan 12-02 (Hand-written docs content)
