---
phase: 04-backtesting-ready-api
plan: 04
subsystem: api
tags: [fastapi, candles, ohlcv, events, date_trunc, sql-aggregation, llms-txt]

# Dependency graph
requires:
  - phase: 04-01
    provides: trades, events, settlements, series tables for querying
  - phase: 04-03
    provides: trades and settlements route patterns, cursor pagination
provides:
  - GET /candles/{ticker} endpoint with 1m/1h/1d SQL-aggregated OHLCV data
  - GET /events and GET /events/{event_ticker} for hierarchy navigation
  - Complete llms.txt and llms-full.txt covering all Phase 4 endpoints
  - EventNotFoundError for event lookup failures
affects: [05-polish-deploy, documentation, ai-agent-discovery]

# Tech tracking
tech-stack:
  added: []
  patterns: [sql-date-trunc-aggregation, dynamic-query-building, event-hierarchy]

key-files:
  created:
    - src/api/services/candles.py
    - src/api/routes/candles.py
    - src/api/routes/events.py
  modified:
    - src/api/main.py
    - src/api/errors.py
    - static/llms.txt
    - static/llms-full.txt

key-decisions:
  - "Candle OHLCV uses array_agg for open/close (first/last trade) and MAX/MIN for high/low"
  - "Empty candle buckets omitted (no forward-fill server-side); documented for consumers"
  - "Events endpoint uses correlated subquery for market_count (acceptable at current scale)"

patterns-established:
  - "SQL aggregation service: separate service file with query constant + async function"
  - "Event hierarchy: events list with market_count subquery, detail with nested markets JOIN"

# Metrics
duration: 5min
completed: 2026-02-15
---

# Phase 4 Plan 4: Candles, Events, and llms.txt Documentation Summary

**GET /candles/{ticker} with SQL date_trunc OHLCV aggregation, GET /events hierarchy endpoints, and comprehensive llms.txt/llms-full.txt covering all 10 data endpoints**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-15T21:07:31Z
- **Completed:** 2026-02-15T21:12:32Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Candlestick endpoint computing OHLCV from raw trades via SQL date_trunc at 1m/1h/1d intervals (3 credits)
- Event hierarchy endpoints: list with market counts and detail with nested markets (1 credit each)
- llms-full.txt expanded to 997 lines with endpoint summary table, candles/events/trades/settlements docs, and updated backtesting workflow with code examples
- All 10 data endpoints, 2 new OpenAPI tags (Candles, Events), and EventNotFoundError registered

## Task Commits

Each task was committed atomically:

1. **Task 1: Create candlestick service and endpoint** - `84e9256` (feat)
2. **Task 2: Create events endpoint, register routers, update llms.txt** - `8f5b716` (feat)

## Files Created/Modified
- `src/api/services/candles.py` - SQL-based OHLCV computation with CANDLE_QUERY and VALID_INTERVALS
- `src/api/routes/candles.py` - GET /candles/{ticker} with interval validation and credit cost 3
- `src/api/routes/events.py` - GET /events (list with filters) and GET /events/{event_ticker} (detail with nested markets)
- `src/api/errors.py` - Added EventNotFoundError following MarketNotFoundError pattern
- `src/api/main.py` - Registered candles and events routers, added Candles and Events OpenAPI tags
- `static/llms.txt` - Reorganized with all endpoint groups and credit costs
- `static/llms-full.txt` - Expanded to 997 lines with complete Phase 4 API documentation

## Decisions Made
- Candle OHLCV uses array_agg with ORDER BY for open (first trade) and close (last trade), MAX/MIN for high/low -- standard approach for SQL-based candlestick computation
- Empty candle buckets produce no rows (documented behavior) -- consumers forward-fill the previous close price; server-side gap-filling would require knowing all possible bucket timestamps
- Events endpoint uses correlated subquery for market_count -- same pattern as markets endpoint for coverage dates; acceptable at current scale

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added EventNotFoundError to errors.py**
- **Found during:** Task 2 (Events endpoint)
- **Issue:** Plan specified adding EventNotFoundError but it was listed within the events route action, not as a separate step
- **Fix:** Added EventNotFoundError class following MarketNotFoundError pattern in errors.py
- **Files modified:** src/api/errors.py
- **Verification:** Import succeeds, error code is "event_not_found" with 404 status
- **Committed in:** 8f5b716 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Error class was implied by the plan but needed explicit creation. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 (Backtesting-Ready API) is now complete with all 4 plans executed
- All 10 data endpoints operational: orderbook, deltas, markets, trades, settlements, candles, events (list + detail)
- llms.txt and llms-full.txt provide complete AI agent discovery for the full API surface
- Ready to proceed to Phase 5 (Polish & Deploy)

---
*Phase: 04-backtesting-ready-api*
*Completed: 2026-02-15*
