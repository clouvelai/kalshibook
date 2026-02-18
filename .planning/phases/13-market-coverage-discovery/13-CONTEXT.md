# Phase 13: Market Coverage Discovery - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can discover which markets have data, how much coverage exists, and where the gaps are. Delivered as a browsable, searchable table of markets grouped by parent event, with pre-computed segment stats served from a materialized view. Coverage segments represent contiguous date ranges — the atomic unit suitable for backtesting.

</domain>

<decisions>
## Implementation Decisions

### Table layout & row style
- Compact rows — one row per market with ticker, title, coverage range, data point counts, and segment count inline
- Markets grouped under their parent event using nested accordion (expanded by default)
- Event header shows event name + market count only (no aggregate stats)

### Event grouping
- Nested accordion pattern — event headers with expand/collapse, expanded by default so users see data immediately
- Series hierarchy is deprioritized — event grouping is the primary organization

### Columns per market row
- Ticker + title
- Coverage range (earliest to latest data date)
- Data point counts (Claude decides which breakdown is most useful — snapshots, deltas, trades, or a meaningful subset)
- Segment count + mini timeline bar

### Search & filter behavior
- Inline search box above the table with filter dropdowns/chips (no sidebar panel)
- Live filter with debounce (~300ms) — results update as user types
- Filter options: Claude decides what's useful based on available data (e.g., active/settled status, event filter, data threshold)
- No-results empty state: simple "No markets match your search" message with a clear-filters link

### Coverage segment display
- Mini timeline bar in each row showing solid colored blocks separated by empty space for gaps — simple and clear
- Text segment count alongside the bar for scannability
- On row expand: each segment shows its date range plus per-segment stats (snapshot count, delta count, trade count)
- Segments are contiguous date ranges — the smallest unit that makes sense to backtest on
- Gaps between segments are implicit (obvious from date jumps between listed segments), not labeled explicitly

### Stats & summary info
- Page-level summary cards above the table (total markets tracked, total data points, overall date range, etc.)
- Numbers abbreviated for scannability ("1.2M snapshots", "45K trades")
- Per-market stats: Claude decides the most useful breakdown for evaluating data quality

### Page navigation
- Claude decides whether this is a new "/coverage" route or integrated into existing dashboard structure, based on what fits best

### Claude's Discretion
- Which specific data point counts to show per market row (snapshots, deltas, trades, combined, or a subset)
- Which filter options to include beyond ticker search
- Page routing — new dashboard page vs. section on existing page
- Summary card content and count
- Exact timeline bar colors and proportions
- Loading states and skeleton design
- Pagination approach for the market table

</decisions>

<specifics>
## Specific Ideas

- Segments are the atomic backtestable unit — a segment is a continuous sequence from start_timestamp to end_timestamp with no internal gaps
- Event grouping is the primary hierarchy; series grouping is secondary/optional
- The feel should be clean and scannable — compact rows, abbreviated numbers, visual timeline bars alongside text data

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-market-coverage-discovery*
*Context gathered: 2026-02-18*
