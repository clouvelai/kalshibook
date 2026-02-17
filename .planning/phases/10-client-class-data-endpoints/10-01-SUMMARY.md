---
phase: 10-client-class-data-endpoints
plan: 01
subsystem: sdk
tags: [httpx, endpoint-methods, sync-async, dataclass-responses, python-sdk]

# Dependency graph
requires:
  - phase: 09-03
    provides: "HttpTransport with request_sync/request_async and KalshiBook client constructor"
  - phase: 09-02
    provides: "Response models (OrderbookResponse, MarketsResponse, etc.) and ResponseMeta"
  - phase: 09-01
    provides: "parse_datetime and _parsing utilities for timezone-safe datetime handling"
provides:
  - "12 public endpoint methods on KalshiBook (6 sync + 6 async)"
  - "_request/_arequest helpers delegating to transport layer"
  - "_parse_response helper for JSON deserialization into typed models"
  - "_ensure_tz helper for defensive UTC normalization of naive datetimes"
affects: [10-02-paginated-endpoints, 11-sdk-testing, 12-pypi-publishing]

# Tech tracking
tech-stack:
  added: []
  patterns: [sync-async-method-pairs, defensive-tz-normalization, optional-params-filtering]

key-files:
  modified:
    - sdk/src/kalshibook/client.py

key-decisions:
  - "No client-side interval validation for get_candles -- server validates for forward-compatibility"
  - "Optional params (list_events filters, orderbook depth) only included when non-None to avoid empty query strings"
  - "_ensure_tz defensively handles naive datetimes (mirrors _parsing.py pattern for outbound serialization)"

patterns-established:
  - "Endpoint method pattern: build params -> _request/_arequest -> _parse_response -> return typed model"
  - "Async counterparts prefixed with 'a' (get_orderbook -> aget_orderbook)"
  - "Optional filter params built into dict only when not None, passed as params or None"

# Metrics
duration: 1min
completed: 2026-02-17
---

# Phase 10 Plan 1: Client Endpoint Methods Summary

**12 typed endpoint methods (6 sync + 6 async) on KalshiBook for orderbook, markets, candles, and events with defensive UTC normalization**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-17T19:33:50Z
- **Completed:** 2026-02-17T19:35:08Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added 12 public endpoint methods to KalshiBook class covering orderbook, markets, candles, and events
- Implemented _request/_arequest/_parse_response/_ensure_tz private helper pipeline
- All methods return typed dataclass responses (OrderbookResponse, MarketsResponse, etc.) not raw dicts
- Naive datetimes defensively converted to UTC-aware before serialization to API

## Task Commits

Each task was committed atomically:

1. **Task 1: Add private helpers and all endpoint methods to KalshiBook client** - `3b1edf4` (feat)

## Files Created/Modified
- `sdk/src/kalshibook/client.py` - Added imports for datetime/httpx/models, 4 private helpers, and 12 public endpoint methods (6 sync + 6 async)

## Decisions Made
- No client-side validation of candle intervals -- server validates for forward-compatibility
- Optional params (list_events category/series_ticker/status, orderbook depth) only included in request when non-None
- _ensure_tz uses same defensive UTC pattern as _parsing.py but for outbound datetime serialization

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 6 non-paginated endpoints wired and callable via KalshiBook class
- Plan 10-02 can add paginated endpoint methods (get_deltas, get_trades, get_settlements) on top of same helper pipeline
- Phase 11 (SDK Testing) can write integration tests against these methods
- Transport layer, models, and exceptions all fully connected through the client

## Self-Check: PASSED

All files verified present. Commit hash 3b1edf4 verified in git log.

---
*Phase: 10-client-class-data-endpoints*
*Completed: 2026-02-17*
