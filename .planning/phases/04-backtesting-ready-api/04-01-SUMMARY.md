---
phase: 04-backtesting-ready-api
plan: 01
subsystem: database
tags: [postgres, partitioning, migrations, pydantic, trades, settlements, events, series]

# Dependency graph
requires:
  - phase: 02-core-api
    provides: "markets, deltas, snapshots tables and partition management function"
provides:
  - "Partitioned trades table (daily, matching deltas pattern)"
  - "Settlements table with denormalized result/value columns"
  - "Events and series hierarchy tables"
  - "markets.series_ticker column for hierarchy linking"
  - "Updated partition function creating trades partitions alongside deltas"
  - "Pydantic models for trades, settlements, candles, events, series endpoints"
affects: [04-02-collector-extension, 04-03-trade-settlement-endpoints, 04-04-candle-hierarchy-endpoints]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Daily partitioning for high-volume trade data (matching deltas pattern)"
    - "Denormalized settlement columns for direct querying (no JOINs needed)"
    - "Event/series hierarchy: series -> events -> markets"

key-files:
  created:
    - supabase/migrations/20260216000001_create_trades.sql
    - supabase/migrations/20260216000002_create_settlements.sql
    - supabase/migrations/20260216000003_create_events_series.sql
    - supabase/migrations/20260216000004_extend_markets.sql
    - supabase/migrations/20260216000005_update_partition_function.sql
  modified:
    - src/api/models.py

key-decisions:
  - "Trades table mirrors deltas partitioning strategy (daily PARTITION BY RANGE on ts)"
  - "Settlements denormalized (no FK to markets) for write performance and direct query access"
  - "Events/series tables are independent (no FKs) -- hierarchy is conceptual via ticker references"

patterns-established:
  - "High-volume tables use daily partitioning with no FK constraints"
  - "Hierarchy linking via ticker columns (series_ticker) rather than FK constraints"

# Metrics
duration: 2min
completed: 2026-02-15
---

# Phase 4 Plan 1: Schema & Models Summary

**Daily-partitioned trades table, denormalized settlements, event/series hierarchy tables, and Pydantic models for all Phase 4 backtesting endpoints**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-15T20:56:36Z
- **Completed:** 2026-02-15T20:58:13Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Trades table with daily partitioning (8 initial partitions), ticker+ts and trade_id indexes
- Settlements table with denormalized result/settlement_value for direct queries without JOINs
- Events and series hierarchy tables with category, status, and series indexes
- markets.series_ticker column linking markets into the hierarchy
- Partition function updated to create trades partitions alongside deltas and snapshots
- 14 new Pydantic models covering trades, settlements, candles, events, and series endpoints

## Task Commits

Each task was committed atomically:

1. **Task 1: Create database migrations** - `f2e0e5a` (feat)
2. **Task 2: Add Pydantic models** - `a925c89` (feat)

## Files Created/Modified
- `supabase/migrations/20260216000001_create_trades.sql` - Partitioned trades table with daily partitions and indexes
- `supabase/migrations/20260216000002_create_settlements.sql` - Settlements table with denormalized result/value columns
- `supabase/migrations/20260216000003_create_events_series.sql` - Series and events hierarchy tables
- `supabase/migrations/20260216000004_extend_markets.sql` - Added series_ticker column to markets
- `supabase/migrations/20260216000005_update_partition_function.sql` - Extended partition function for trades
- `src/api/models.py` - 14 new Pydantic models for Phase 4 endpoints

## Decisions Made
- Trades table mirrors deltas partitioning strategy (daily PARTITION BY RANGE on ts) for consistency
- Settlements denormalized with no FK to markets -- same write performance reasoning as deltas
- Events/series tables are independent (no FKs) -- hierarchy is conceptual via ticker references

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All tables ready for collector extension (Plan 02) to write trades/settlements/events/series data
- All Pydantic models ready for API endpoint implementation (Plans 03-04)
- Partition function handles trades alongside deltas for ongoing partition management

## Self-Check: PASSED

All 7 files verified present. Both task commits (`f2e0e5a`, `a925c89`) confirmed in git log.

---
*Phase: 04-backtesting-ready-api*
*Completed: 2026-02-15*
