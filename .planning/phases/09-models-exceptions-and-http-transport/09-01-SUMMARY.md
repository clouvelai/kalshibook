---
phase: 09-models-exceptions-and-http-transport
plan: 01
subsystem: sdk
tags: [exceptions, datetime, parsing, python-sdk, stdlib]

# Dependency graph
requires:
  - phase: 08-sdk-scaffolding
    provides: "SDK package structure with src layout and stub modules"
provides:
  - "KalshiBookError base exception with status_code, response_body, message"
  - "5 specific exception subclasses for SDK error handling"
  - "parse_datetime helper for cross-version ISO 8601 parsing"
affects: [09-02, 09-03, sdk-client, sdk-http-transport, sdk-models]

# Tech tracking
tech-stack:
  added: []
  patterns: [exception-hierarchy-with-context, cross-version-datetime-parsing]

key-files:
  created:
    - sdk/src/kalshibook/_parsing.py
  modified:
    - sdk/src/kalshibook/exceptions.py

key-decisions:
  - "SDK exceptions carry status_code/response_body (not code/status like server errors) to match HTTP client context"
  - "parse_datetime normalizes Z suffix to +00:00 for Python 3.10 compatibility"

patterns-established:
  - "Exception hierarchy: KalshiBookError base with keyword-only status_code and response_body"
  - "Defensive timezone handling: all parsed datetimes guaranteed timezone-aware"

# Metrics
duration: 1min
completed: 2026-02-17
---

# Phase 9 Plan 1: Exceptions and Parsing Summary

**SDK exception hierarchy with 5 typed error classes and cross-version ISO 8601 datetime parser using only stdlib**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-17T18:18:53Z
- **Completed:** 2026-02-17T18:20:09Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- KalshiBookError base exception with status_code, response_body, and message attributes
- 5 specific exception subclasses: AuthenticationError, RateLimitError, CreditsExhaustedError, MarketNotFoundError, ValidationError
- parse_datetime utility handling Z suffix, +00:00 suffix, None input, empty string, and naive datetime fallback to UTC

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement SDK exception hierarchy** - `e06acdd` (feat)
2. **Task 2: Implement datetime parsing utility** - `18ed23a` (feat)

## Files Created/Modified
- `sdk/src/kalshibook/exceptions.py` - Complete exception hierarchy with KalshiBookError base and 5 subclasses
- `sdk/src/kalshibook/_parsing.py` - parse_datetime helper for cross-version ISO 8601 parsing

## Decisions Made
- SDK exceptions use `status_code` and `response_body` attributes (not `code` and `status` like the server's `src/api/errors.py`) -- designed for HTTP client context rather than server handler context
- `parse_datetime` normalizes Z suffix to +00:00 rather than using `dateutil` -- avoids adding external dependency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Exception hierarchy ready for import by `_http.py` (error mapping) and `client.py` (validation)
- `parse_datetime` ready for import by `models.py` (from_dict factories)
- Both modules have zero external dependencies (stdlib only)

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 09-models-exceptions-and-http-transport*
*Completed: 2026-02-17*
