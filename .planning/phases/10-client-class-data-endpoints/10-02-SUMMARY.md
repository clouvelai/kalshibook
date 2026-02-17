---
phase: 10-client-class-data-endpoints
plan: 02
subsystem: testing
tags: [pytest, pytest-httpx, async-tests, endpoint-testing, python-sdk]

# Dependency graph
requires:
  - phase: 10-01
    provides: "12 public endpoint methods on KalshiBook (6 sync + 6 async)"
  - phase: 09-02
    provides: "Response models (OrderbookResponse, MarketsResponse, etc.) and exception classes"
  - phase: 09-03
    provides: "HttpTransport with request_sync/request_async"
provides:
  - "14 endpoint tests covering all 6 sync methods + 3 representative async methods"
  - "ResponseMeta extraction test validating credit header parsing"
  - "Error mapping tests for MarketNotFoundError (404) and ValidationError (422)"
  - "Naive datetime UTC conversion test for outbound request serialization"
  - "Optional filter param inclusion/exclusion test for list_events"
affects: [12-pypi-publishing]

# Tech tracking
tech-stack:
  added: []
  patterns: [pytest-httpx-match-params, sync-async-test-coverage]

key-files:
  created:
    - sdk/tests/test_endpoints.py
  modified: []

key-decisions:
  - "pytest-httpx match_params used for query-parameterized endpoints (exact URL matching fails with query strings)"
  - "3 representative async tests sufficient -- covers POST-body, GET-path-param, GET-query-param dispatch patterns"
  - "Tasks 1 and 2 committed together since both write to same file"

patterns-established:
  - "pytest-httpx mock pattern: add_response with url + method + match_params for query-parameterized endpoints"
  - "Async tests use sync=False client constructor and await aclose() for cleanup"

# Metrics
duration: 2min
completed: 2026-02-17
---

# Phase 10 Plan 2: Endpoint Tests Summary

**14 pytest-httpx tests verifying all sync/async endpoint methods, error mapping, ResponseMeta extraction, and naive datetime handling**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-17T19:37:23Z
- **Completed:** 2026-02-17T19:39:34Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments
- 14 tests covering all 6 endpoint methods (sync) with 3 representative async variants
- Error mapping verified: 404 raises MarketNotFoundError, 422 raises ValidationError
- ResponseMeta credits_used/credits_remaining correctly extracted from response headers
- Naive datetime defensive UTC normalization verified on outbound POST body
- Optional filter param inclusion/exclusion tested for list_events

## Task Commits

Tasks 1 and 2 committed together (both write to the same test file):

1. **Task 1 + Task 2: Sync and async endpoint tests** - `cb74804` (test)

## Files Created/Modified
- `sdk/tests/test_endpoints.py` - 14 endpoint tests: 6 sync happy-path, ResponseMeta, 2 error mapping, naive datetime, filter params, 3 async

## Decisions Made
- Used pytest-httpx `match_params` kwarg for URL matching on query-parameterized endpoints (candles, events filters) -- exact URL matching fails when query strings are present
- 3 async tests (POST-body, GET-path-param, GET-query-param) chosen as representative since the async dispatch path is identical across all methods
- Merged Task 1 and Task 2 into single commit since both write to the same file

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pytest-httpx URL matching for query-parameterized endpoints**
- **Found during:** Task 1 (test_get_candles, test_list_events_filters)
- **Issue:** pytest-httpx 0.36 `url` matcher performs exact string match including query parameters, so `url=".../candles/KXBTC-TEST"` did not match the actual request URL which includes `?start_time=...&end_time=...&interval=1h`
- **Fix:** Added `match_params` kwarg to `add_response` for candles and events filter tests
- **Files modified:** sdk/tests/test_endpoints.py
- **Verification:** All 14 tests pass
- **Committed in:** cb74804

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for test correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 6 endpoint methods fully tested with deterministic mocks
- Phase 10 complete -- all endpoint methods implemented and tested
- Phase 12 (PyPI publishing) can proceed with confidence in endpoint correctness
- Full test suite: 18 tests (4 import + 14 endpoint) all passing

## Self-Check: PASSED

All files verified present. Commit hash cb74804 verified in git log.

---
*Phase: 10-client-class-data-endpoints*
*Completed: 2026-02-17*
