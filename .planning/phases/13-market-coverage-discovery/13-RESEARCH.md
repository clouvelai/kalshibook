# Phase 13: Market Coverage Discovery - Research

**Researched:** 2026-02-18
**Domain:** PostgreSQL materialized views, gaps-and-islands SQL, Next.js dashboard UI (TanStack Table expanding rows)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Table layout & row style
- Compact rows -- one row per market with ticker, title, coverage range, data point counts, and segment count inline
- Markets grouped under their parent event using nested accordion (expanded by default)
- Event header shows event name + market count only (no aggregate stats)

#### Event grouping
- Nested accordion pattern -- event headers with expand/collapse, expanded by default so users see data immediately
- Series hierarchy is deprioritized -- event grouping is the primary organization

#### Columns per market row
- Ticker + title
- Coverage range (earliest to latest data date)
- Data point counts (Claude decides which breakdown is most useful -- snapshots, deltas, trades, or a meaningful subset)
- Segment count + mini timeline bar

#### Search & filter behavior
- Inline search box above the table with filter dropdowns/chips (no sidebar panel)
- Live filter with debounce (~300ms) -- results update as user types
- Filter options: Claude decides what's useful based on available data (e.g., active/settled status, event filter, data threshold)
- No-results empty state: simple "No markets match your search" message with a clear-filters link

#### Coverage segment display
- Mini timeline bar in each row showing solid colored blocks separated by empty space for gaps -- simple and clear
- Text segment count alongside the bar for scannability
- On row expand: each segment shows its date range plus per-segment stats (snapshot count, delta count, trade count)
- Segments are contiguous date ranges -- the smallest unit that makes sense to backtest on
- Gaps between segments are implicit (obvious from date jumps between listed segments), not labeled explicitly

#### Stats & summary info
- Page-level summary cards above the table (total markets tracked, total data points, overall date range, etc.)
- Numbers abbreviated for scannability ("1.2M snapshots", "45K trades")
- Per-market stats: Claude decides the most useful breakdown for evaluating data quality

#### Page navigation
- Claude decides whether this is a new "/coverage" route or integrated into existing dashboard structure, based on what fits best

### Claude's Discretion
- Which specific data point counts to show per market row (snapshots, deltas, trades, combined, or a subset)
- Which filter options to include beyond ticker search
- Page routing -- new dashboard page vs. section on existing page
- Summary card content and count
- Exact timeline bar colors and proportions
- Loading states and skeleton design
- Pagination approach for the market table

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

## Summary

Phase 13 delivers a Market Coverage Discovery page -- a browsable, searchable table where users discover which markets have data, how much coverage exists, and where the gaps are. The core technical challenge is computing coverage **segments** (contiguous date ranges) from three partitioned high-volume tables (snapshots, deltas, trades), doing so performantly via a materialized view, and presenting the results in a nested accordion table with mini timeline bars.

The backend work centers on a PostgreSQL materialized view (`market_coverage_stats`) that pre-computes per-market segment information using the gaps-and-islands SQL pattern. This view aggregates across snapshots, deltas, and trades to find contiguous date ranges and compute per-segment counts. A `REFRESH MATERIALIZED VIEW CONCURRENTLY` call (triggered from the API on a schedule or manual endpoint) keeps it current. The frontend work adds a new `/coverage` dashboard route with a TanStack Table using expanding rows for the event-grouped accordion, a debounced search input, filter chips, and a custom mini timeline bar component rendered inline per row.

**Primary recommendation:** Build a single materialized view with a unique index, expose it through a new unauthenticated (dashboard-internal) FastAPI endpoint, and consume it from a new Next.js page at `/coverage` using TanStack Table's expanding row model for the event accordion.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL 17 | 17.x | Materialized view, gaps-and-islands query | Already in use; mat views are native PG feature |
| asyncpg | existing | Query the materialized view from FastAPI | Already in use for all API routes |
| FastAPI | existing | New `/coverage` endpoint serving pre-computed data | Already in use for all API routes |
| Next.js | 15.5.12 | New `/coverage` dashboard page | Already in use |
| @tanstack/react-table | 8.21.3 | Expanding rows for event accordion, column definitions | Already installed in dashboard |
| Tailwind CSS | 4.x | Styling for timeline bar, cards, table | Already in use |
| lucide-react | 0.564.0 | Icons for expand/collapse, search, filters | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui components | existing | Card, Badge, Input, Skeleton, Table | Already installed -- use for summary cards, filter inputs, loading states |
| sonner | 2.0.7 | Toast notifications for errors | Already installed -- use for API error feedback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Materialized view | Regular view | No caching -- would scan partitions on every request; violates COVR-04 |
| Materialized view | Application-level cache (Redis) | Extra infrastructure; PG mat view is simpler and already available |
| TanStack Table expanding | Custom accordion divs | Lose column alignment, sorting capability, and header management |
| Inline timeline bar (div) | Canvas/SVG timeline | Over-engineered for simple colored blocks; divs with flexbox are sufficient |

**Installation:**
No new packages needed. All dependencies are already installed.

## Architecture Patterns

### Recommended Project Structure
```
supabase/migrations/
  20260218000001_create_coverage_matview.sql   # Materialized view + unique index + refresh function

src/api/routes/
  coverage.py                                   # GET /coverage/stats endpoint (JWT-auth, no credits)

src/api/models.py                               # New response models (CoverageSegment, MarketCoverage, etc.)

dashboard/src/
  app/(dashboard)/coverage/
    page.tsx                                    # Coverage page (new route)
  components/coverage/
    coverage-table.tsx                          # TanStack Table with expanding rows
    coverage-search.tsx                         # Debounced search + filter chips
    coverage-summary-cards.tsx                  # Page-level summary stats
    coverage-timeline-bar.tsx                   # Mini timeline bar component
    coverage-segment-detail.tsx                 # Expanded row segment details
  types/api.ts                                  # Extended with coverage types
  lib/api.ts                                    # Extended with coverage API method
```

### Pattern 1: Gaps-and-Islands for Coverage Segments
**What:** SQL pattern using LAG window function + cumulative SUM to identify contiguous date ranges in time-series data. Each "island" becomes a coverage segment.
**When to use:** Whenever you need to find contiguous ranges in date-bucketed data with potential gaps.
**How it works:**
1. Bucket each data source (snapshots, deltas, trades) by date
2. UNION ALL the distinct dates across all three sources per market
3. Use `LAG(data_date) OVER (PARTITION BY market_ticker ORDER BY data_date)` to find previous date
4. Flag boundaries: when `data_date - prev_date > 1 day`, mark as new segment start
5. Use `SUM(boundary_flag) OVER (...)` to assign segment IDs
6. GROUP BY segment ID to get `MIN(data_date)` / `MAX(data_date)` per segment

**Example:**
```sql
-- Step 1: Get distinct data dates per market from all sources
WITH data_dates AS (
    SELECT market_ticker, captured_at::date AS data_date FROM snapshots
    UNION
    SELECT market_ticker, ts::date AS data_date FROM deltas
    UNION
    SELECT market_ticker, ts::date AS data_date FROM trades
),
-- Step 2: Detect segment boundaries using LAG
with_boundaries AS (
    SELECT
        market_ticker,
        data_date,
        CASE
            WHEN data_date - LAG(data_date) OVER (
                PARTITION BY market_ticker ORDER BY data_date
            ) > 1
            THEN 1
            ELSE 0
        END AS is_boundary
    FROM data_dates
),
-- Step 3: Assign segment IDs via cumulative sum
with_segments AS (
    SELECT
        market_ticker,
        data_date,
        SUM(is_boundary) OVER (
            PARTITION BY market_ticker ORDER BY data_date
        ) AS segment_id
    FROM with_boundaries
)
-- Step 4: Aggregate to segment ranges
SELECT
    market_ticker,
    segment_id,
    MIN(data_date) AS segment_start,
    MAX(data_date) AS segment_end,
    COUNT(*) AS days_covered
FROM with_segments
GROUP BY market_ticker, segment_id
ORDER BY market_ticker, segment_start;
```
Source: Gaps-and-islands SQL pattern, well-documented in PostgreSQL community (see Sources section)

### Pattern 2: Materialized View with CONCURRENTLY Refresh
**What:** A pre-computed snapshot of the coverage query, stored as a table. Refreshed periodically without blocking reads.
**When to use:** When coverage stats must load in under 2 seconds (COVR-04) and the underlying query scans millions of rows across partitioned tables.
**Requirements:**
- MUST have at least one UNIQUE index (required for CONCURRENTLY)
- The unique index must use only column names (no expressions, no WHERE clause)
- The view must already be populated (not `WITH NO DATA`) before first concurrent refresh

**Example:**
```sql
CREATE MATERIALIZED VIEW market_coverage_stats AS
    -- [the gaps-and-islands query from Pattern 1, plus aggregated counts]
WITH DATA;

-- Required for REFRESH CONCURRENTLY
CREATE UNIQUE INDEX idx_coverage_stats_pk
    ON market_coverage_stats (market_ticker, segment_id);

-- Refresh function callable from API
CREATE OR REPLACE FUNCTION refresh_coverage_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY market_coverage_stats;
END;
$$ LANGUAGE plpgsql;
```
Source: [PostgreSQL 18 docs on REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html)

### Pattern 3: TanStack Table Expanding Rows for Event Accordion
**What:** Using TanStack Table's `getExpandedRowModel` with `subRows` to render markets nested under event headers.
**When to use:** When data has a parent-child hierarchy (events -> markets) and you want column-aligned expandable groups.
**Key configuration:**
- Data shaped as `EventGroup[]` where each event has a `subRows: MarketRow[]` array
- `getSubRows: (row) => row.subRows` in table options
- `getExpandedRowModel()` feature enabled
- Custom row rendering: event rows span full width; market rows render individual cells
- Default expanded state: `expanded: true` (all groups expanded by default)

### Pattern 4: Dashboard-Internal Endpoint (No Credits)
**What:** A FastAPI endpoint authenticated via Supabase JWT (like `/keys`) rather than API key + credits.
**When to use:** For dashboard-only data that authenticated users should access without consuming credits.
**Why:** Coverage stats are a dashboard feature, not a billing-metered API endpoint. The existing `get_authenticated_user` dependency provides JWT auth without credit deduction.

### Anti-Patterns to Avoid
- **Live partition scans on page load:** Never query snapshots/deltas/trades directly for coverage stats. Always use the materialized view. The existing `list_markets` endpoint already does this (correlated subqueries on snapshots/deltas) -- this phase replaces that pattern with pre-computed data.
- **Single first/last timestamp per market:** This hides gaps. A market with data on days 1-3 and 7-10 MUST show two segments, not "Jan 1 - Jan 10" (COVR-05).
- **Refreshing mat view on every request:** Expensive. Refresh on a schedule (e.g., every 15 minutes via API cron or on-demand admin endpoint).
- **Over-complex timeline bars:** Use simple `<div>` elements with percentage-based widths inside a flex container. No Canvas/SVG needed for colored blocks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gaps-and-islands detection | Custom app-level date iteration | PostgreSQL LAG + SUM window functions | SQL handles millions of rows efficiently; app-level would require loading all dates into memory |
| Pre-computed stats | Redis cache or app-level caching | PostgreSQL materialized view | Native PG feature, no extra infrastructure, CONCURRENTLY avoids downtime |
| Expanding/accordion table | Custom div-based accordion | TanStack Table `getExpandedRowModel` | Already installed; gives column alignment, state management, keyboard nav for free |
| Debounced search | Manual setTimeout/clearTimeout | useEffect with setTimeout pattern (or useDeferredValue) | Standard React pattern, ~10 lines |
| Number abbreviation | Custom formatting logic | Intl.NumberFormat with `notation: "compact"` | Browser-native, handles locales, handles "K", "M", "B" automatically |

**Key insight:** The entire coverage computation belongs in SQL (materialized view), not application code. PostgreSQL's window functions handle the gaps-and-islands pattern natively and efficiently across partitioned tables.

## Common Pitfalls

### Pitfall 1: Missing UNIQUE index on materialized view
**What goes wrong:** `REFRESH MATERIALIZED VIEW CONCURRENTLY` fails with "cannot refresh concurrently" error.
**Why it happens:** CONCURRENTLY requires at least one unique index that covers all rows (no WHERE clause, no expression).
**How to avoid:** Create the unique index immediately after `CREATE MATERIALIZED VIEW`. Use `(market_ticker, segment_id)` as the composite key.
**Warning signs:** First refresh works (non-concurrent), subsequent ones fail when you add CONCURRENTLY.

### Pitfall 2: Materialized view query scans ALL partitions
**What goes wrong:** The mat view refresh takes minutes because it scans every partition of snapshots, deltas, and trades.
**Why it happens:** UNION queries across partitioned tables may not benefit from partition pruning when no WHERE clause restricts the date range.
**How to avoid:** Accept that mat view refresh is an intentionally expensive batch operation. Schedule it during low-traffic periods. For initial implementation, full scans are acceptable -- optimize later if needed with incremental approaches. The key constraint is that **reads** are fast (just querying the mat view), not that **refreshes** are fast.
**Warning signs:** Refresh takes >30 seconds on production data volume.

### Pitfall 3: Date bucketing granularity mismatch
**What goes wrong:** Segments appear fragmented because the gap threshold is too small (e.g., treating a 2-hour gap within the same day as a segment boundary).
**Why it happens:** Using timestamp-level granularity instead of date-level for gap detection.
**How to avoid:** Bucket all timestamps to DATE (`::date` cast) before running gaps-and-islands. A gap is defined as a missing calendar day, not a missing hour. This matches user mental model: "data exists for Feb 13-15, gap, then Feb 18-20" = 2 segments.
**Warning signs:** Markets show dozens of tiny segments when they should show 1-2.

### Pitfall 4: Expanded-by-default causes performance issues with large lists
**What goes wrong:** Rendering 200+ markets all expanded creates a huge DOM, causing slow initial paint.
**Why it happens:** All event groups expanded by default means all market rows render immediately.
**How to avoid:** Implement virtual scrolling or paginate at the event group level. Start with pagination (20-30 events per page). If performance is still an issue, add `@tanstack/react-virtual` later. Pagination is the simpler first approach.
**Warning signs:** Page takes >1 second to render after data arrives.

### Pitfall 5: Concurrent materialized view refresh blocks other refreshes
**What goes wrong:** Two concurrent refresh calls cause one to fail or block.
**Why it happens:** PostgreSQL only allows one REFRESH at a time per materialized view, even with CONCURRENTLY.
**How to avoid:** Use a database advisory lock in the refresh function, or handle the error gracefully in the API. Only one refresh should be in-flight at any time.
**Warning signs:** Error logs showing "could not obtain lock" during refresh.

### Pitfall 6: Empty timeline bar for markets with no segments
**What goes wrong:** Markets with no data (just metadata from discovery) show a broken or empty timeline bar.
**Why it happens:** The materialized view only contains markets with actual data. Discovered-but-empty markets have no rows.
**How to avoid:** LEFT JOIN markets to the coverage view. Markets with no coverage rows display "No data yet" instead of a timeline bar.
**Warning signs:** Markets disappear from coverage page despite being in the markets table.

## Code Examples

Verified patterns from the existing codebase and official sources:

### Coverage Materialized View (Complete SQL)
```sql
-- Source: Gaps-and-islands pattern + PostgreSQL materialized views
CREATE MATERIALIZED VIEW market_coverage_stats AS
WITH data_dates AS (
    -- Distinct dates with data per market, per source
    SELECT market_ticker, captured_at::date AS data_date, 'snapshot' AS source
    FROM snapshots
    UNION ALL
    SELECT market_ticker, ts::date AS data_date, 'delta' AS source
    FROM deltas
    UNION ALL
    SELECT market_ticker, ts::date AS data_date, 'trade' AS source
    FROM trades
),
distinct_dates AS (
    SELECT DISTINCT market_ticker, data_date
    FROM data_dates
),
with_boundaries AS (
    SELECT
        market_ticker,
        data_date,
        CASE
            WHEN data_date - LAG(data_date) OVER (
                PARTITION BY market_ticker ORDER BY data_date
            ) > 1
            THEN 1
            ELSE 0
        END AS is_boundary
    FROM distinct_dates
),
with_segments AS (
    SELECT
        market_ticker,
        data_date,
        SUM(is_boundary) OVER (
            PARTITION BY market_ticker ORDER BY data_date
        ) AS segment_id
    FROM with_boundaries
),
segments AS (
    SELECT
        market_ticker,
        segment_id,
        MIN(data_date) AS segment_start,
        MAX(data_date) AS segment_end,
        COUNT(*) AS days_covered
    FROM with_segments
    GROUP BY market_ticker, segment_id
)
SELECT
    s.market_ticker,
    s.segment_id,
    s.segment_start,
    s.segment_end,
    s.days_covered,
    -- Per-segment counts (correlated subqueries, acceptable for mat view build)
    (SELECT COUNT(*) FROM snapshots
     WHERE market_ticker = s.market_ticker
       AND captured_at::date BETWEEN s.segment_start AND s.segment_end
    ) AS snapshot_count,
    (SELECT COUNT(*) FROM deltas
     WHERE market_ticker = s.market_ticker
       AND ts::date BETWEEN s.segment_start AND s.segment_end
    ) AS delta_count,
    (SELECT COUNT(*) FROM trades
     WHERE market_ticker = s.market_ticker
       AND ts::date BETWEEN s.segment_start AND s.segment_end
    ) AS trade_count
FROM segments s
WITH DATA;

CREATE UNIQUE INDEX idx_coverage_stats_pk
    ON market_coverage_stats (market_ticker, segment_id);

CREATE INDEX idx_coverage_stats_ticker
    ON market_coverage_stats (market_ticker);
```

### FastAPI Coverage Endpoint Pattern
```python
# Source: Existing codebase pattern (events.py, markets.py)
@router.get("/coverage/stats")
async def get_coverage_stats(
    request: Request,
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    event_ticker: str | None = Query(default=None),
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Coverage stats from materialized view. Dashboard-internal, no credits."""
    # Query market_coverage_stats mat view joined with markets + events
    # Group results by event_ticker for frontend consumption
    ...
```

### TanStack Table Expanding Rows Setup
```typescript
// Source: TanStack Table v8 docs (expanding guide)
import {
  useReactTable,
  getCoreRowModel,
  getExpandedRowModel,
  type ExpandedState,
} from "@tanstack/react-table";

const [expanded, setExpanded] = useState<ExpandedState>(true); // all expanded by default

const table = useReactTable({
  data: eventGroups, // EventGroup[] with subRows: MarketRow[]
  columns,
  state: { expanded },
  onExpandedChange: setExpanded,
  getSubRows: (row) => row.subRows,
  getCoreRowModel: getCoreRowModel(),
  getExpandedRowModel: getExpandedRowModel(),
});
```

### Debounced Search Input
```typescript
// Source: TanStack Table docs (filters example) + standard React pattern
function DebouncedInput({
  value: initialValue,
  onChange,
  debounce = 300,
  ...props
}: {
  value: string;
  onChange: (value: string) => void;
  debounce?: number;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange">) {
  const [value, setValue] = useState(initialValue);

  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      onChange(value);
    }, debounce);
    return () => clearTimeout(timeout);
  }, [value, debounce, onChange]);

  return <Input {...props} value={value} onChange={(e) => setValue(e.target.value)} />;
}
```

### Number Abbreviation
```typescript
// Source: Browser-native Intl.NumberFormat API
function formatCompact(n: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}
// formatCompact(1234567) => "1.2M"
// formatCompact(45000) => "45K"
// formatCompact(892) => "892"
```

### Mini Timeline Bar Component
```typescript
// Source: Custom component pattern for coverage visualization
function TimelineBar({
  segments,
  overallStart,
  overallEnd,
}: {
  segments: { start: string; end: string }[];
  overallStart: string;
  overallEnd: string;
}) {
  const totalDays = daysBetween(overallStart, overallEnd) || 1;

  return (
    <div className="flex h-2 w-full rounded-full bg-muted overflow-hidden">
      {segments.map((seg, i) => {
        const leftPct = (daysBetween(overallStart, seg.start) / totalDays) * 100;
        const widthPct = (daysBetween(seg.start, seg.end) / totalDays) * 100;
        return (
          <div
            key={i}
            className="absolute h-full rounded-sm bg-primary"
            style={{ left: `${leftPct}%`, width: `${Math.max(widthPct, 1)}%` }}
          />
        );
      })}
    </div>
  );
}
```

## Discretion Recommendations

Based on the codebase analysis and user context, here are recommendations for areas marked as Claude's Discretion:

### Data point counts per market row
**Recommend:** Show three counts inline: snapshots, deltas, trades. All three are distinct data types that users care about for different backtesting scenarios.
- Snapshots = full orderbook state (baseline for reconstruction)
- Deltas = individual price level changes (granularity indicator)
- Trades = executed trades (trading activity indicator)
**Format:** "1.2K snap | 45K delta | 892 trades" using compact notation.

### Filter options beyond ticker search
**Recommend:** Three filters:
1. **Status** dropdown: active / settled / all (maps to `markets.status`)
2. **Event** dropdown: list of event tickers (populated from data)
3. **Min data points** threshold: e.g., "Markets with 1K+ data points" (quick way to find well-covered markets)

### Page routing
**Recommend:** New `/coverage` route as a separate dashboard page. Reasoning:
- It's a distinct use case from Overview (which shows billing/keys)
- Needs its own layout (summary cards + large table)
- Add to sidebar navigation between "Overview" and "Playground" with a `Database` or `BarChart3` lucide icon

### Summary card content
**Recommend:** Four summary cards:
1. **Markets Tracked** -- total markets with any data
2. **Total Snapshots** -- sum across all markets, compact notation
3. **Total Deltas** -- sum across all markets, compact notation
4. **Date Range** -- earliest to latest data date across all markets

### Timeline bar colors
**Recommend:** Use `bg-primary` (the theme's primary color) for segment blocks against `bg-muted` background. Simple, consistent with the existing design system. No need for multiple colors.

### Loading states
**Recommend:** Use existing `<Skeleton>` component matching the pattern in `page.tsx` (Overview):
- 4 skeleton cards for summary stats
- Full-width skeleton block for the table
- Skeleton rows within the table during incremental loading

### Pagination approach
**Recommend:** Paginate at the **event group** level, not the market level. Show 20 events per page (each with all their markets expanded). This keeps the accordion grouping intact while limiting DOM size. Use simple prev/next pagination (not infinite scroll) since coverage data is finite and users need to browse systematically.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Live COUNT(*) on partitioned tables | Materialized views for pre-computed stats | Always been best practice | Critical for COVR-04 -- live scans on partitioned tables are O(partitions) |
| First/last timestamp only | Gaps-and-islands segment detection | Always been available in SQL | Required by COVR-05 -- segments must reflect actual gaps |
| Custom expanding UI components | TanStack Table getExpandedRowModel | TanStack Table v8 (2022+) | Built-in state management, keyboard nav, column alignment |
| Manual debounce hooks | React useDeferredValue or standard setTimeout pattern | React 18+ | Both work; setTimeout is more explicit for the 300ms requirement |

**Deprecated/outdated:**
- `@tanstack/react-table` v7 expanding API (v8 API is different -- use `getExpandedRowModel`, not `useExpanded`)
- PostgreSQL multirange types (PG 14+) could theoretically replace gaps-and-islands, but the CTE approach is more readable and well-understood

## Open Questions

1. **Materialized view refresh trigger**
   - What we know: REFRESH MATERIALIZED VIEW CONCURRENTLY is the mechanism. pg_cron is available in Supabase hosted but may not be in local dev.
   - What's unclear: Whether to use pg_cron (database-level), a FastAPI background task, or an admin API endpoint for triggering refresh.
   - Recommendation: Start with a **FastAPI admin endpoint** (`POST /coverage/refresh`) that calls the SQL function. This works identically in local and production. pg_cron can be added later in production for automated scheduling. The endpoint can be called manually during development and via cron job externally in production.

2. **Materialized view refresh frequency**
   - What we know: Data arrives continuously from the WebSocket collector. Coverage stats are not real-time critical.
   - What's unclear: Optimal refresh interval -- every 15 minutes? Every hour? On-demand only?
   - Recommendation: Start with **on-demand** (manual refresh via admin endpoint). The coverage page can show "Last refreshed: X minutes ago" to set expectations. Add scheduled refresh later based on usage patterns.

3. **Per-segment counts performance in materialized view**
   - What we know: Correlated subqueries for per-segment snapshot/delta/trade counts will scan partitions during refresh.
   - What's unclear: How slow this becomes with months of data across hundreds of markets.
   - Recommendation: Start with the correlated subquery approach (simpler SQL). If refresh becomes too slow (>60 seconds), optimize by pre-aggregating daily counts in a separate view and joining. This is an optimization, not a design change.

4. **Markets without events**
   - What we know: The `markets` table has `event_ticker` which may be NULL for some markets.
   - What's unclear: How many markets lack event_ticker in practice.
   - Recommendation: Group ungrouped markets under an "Ungrouped Markets" pseudo-event at the bottom of the table. This handles the edge case without breaking the accordion pattern.

## Sources

### Primary (HIGH confidence)
- [PostgreSQL 18: REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html) -- CONCURRENTLY requirements, locking behavior, unique index requirement
- [TanStack Table v8 Expanding Guide](https://tanstack.com/table/v8/docs/guide/expanding) -- getExpandedRowModel, getSubRows, expanded state management
- Existing codebase: `src/api/routes/markets.py`, `src/api/routes/events.py`, `src/api/models.py` -- established patterns for FastAPI routes, response models, database queries
- Existing codebase: `dashboard/src/components/keys/keys-table.tsx`, `dashboard/src/app/(dashboard)/page.tsx` -- established patterns for table rendering, loading states, error handling

### Secondary (MEDIUM confidence)
- [Solving Gaps and Islands in PostgreSQL (Atomic Object)](https://spin.atomicobject.com/2021/09/27/gaps-islands-problem-postgres/) -- LAG + SUM pattern for identifying contiguous ranges, verified with PostgreSQL docs
- [Finding Gaps in Time Series Data (End Point Dev)](https://www.endpointdev.com/blog/2020/10/postgresql-finding-gaps-in-time-series-data/) -- generate_series + LEFT JOIN approach for gap detection
- [TanStack Table Filters Example](https://tanstack.com/table/latest/docs/framework/react/examples/filters) -- DebouncedInput component pattern
- [Supabase pg_cron documentation](https://supabase.com/docs/guides/database/extensions/pg_cron) -- cron.schedule() for automated refresh (production use)

### Tertiary (LOW confidence)
- pg_cron availability in Supabase local development -- not confirmed. Recommend API-triggered refresh as fallback.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in the codebase; no new dependencies
- Architecture: HIGH -- gaps-and-islands is a well-documented SQL pattern; materialized views are native PG; TanStack Table expanding is documented
- Pitfalls: HIGH -- based on PostgreSQL docs (CONCURRENTLY requirements) and practical experience with partitioned tables
- Discretion recommendations: MEDIUM -- based on codebase patterns and domain analysis, but user may have preferences

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable domain -- SQL patterns and React table libraries don't change rapidly)
