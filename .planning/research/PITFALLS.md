# Pitfalls Research: Discovery, Replay & Coverage Features

**Domain:** Orderbook replay visualization, market coverage dashboards, and data discovery features added to existing financial data API platform (KalshiBook)
**Researched:** 2026-02-18
**Confidence:** HIGH (verified against existing codebase architecture, PostgreSQL partitioning documentation, browser rendering performance research, and billing system analysis)

## Critical Pitfalls

### Pitfall 1: Browser Memory Explosion from Unbounded Replay Data Transfer

**What goes wrong:**
The replay visualization loads an entire market's orderbook history into the browser. A replay of a single active market for one day requires fetching the initial snapshot (JSONB with up to 99 yes levels + 99 no levels) plus all deltas between start and end time. For a market like BTC with continuous trading, a 24-hour period can generate 50,000-200,000+ delta records. At ~100 bytes per delta in JSON, that is 5-20MB of raw JSON transferred to the browser -- and once parsed into JavaScript objects, memory usage triples to 15-60MB. A user who opens multiple replays, or replays a week of data, can push the browser tab past 500MB and trigger an out-of-memory crash on mobile devices or low-RAM machines.

**Why it happens:**
The existing `reconstruct_orderbook()` function (in `src/api/services/reconstruction.py`) reconstructs a single point-in-time state server-side. A replay needs N states over time. The naive approach is to call the orderbook endpoint N times (expensive in credits and latency) or to create a new "replay" endpoint that returns ALL deltas in one response. Both fail: the per-request approach costs `5 credits * N` and is slow; the bulk approach dumps all data into a single JSON response that must be fully loaded before the browser can start rendering.

The existing deltas endpoint (`/deltas`) returns paginated results with a max of 1000 per page, which is good for API consumers, but for browser-based replay you need the full dataset in-memory to reconstruct states at arbitrary points. There is no intermediate representation -- no server-side pre-processing into "keyframes" that would reduce the data transfer.

**How to avoid:**
- Create a dedicated **replay endpoint** that does server-side reconstruction at configurable intervals (e.g., one state every 30 seconds) and returns a time series of orderbook snapshots, not raw deltas. This shifts the O(N) delta processing from the browser to the server where it belongs.
- Implement **streaming delivery** using Server-Sent Events (SSE) or chunked JSON (Next.js supports streaming in App Router). The browser starts rendering the first frame while subsequent frames are still being computed. The existing Next.js dashboard already uses the App Router, so streaming is architecturally compatible.
- Set a **hard maximum time range** for replay requests (e.g., 4 hours max per request). Longer ranges require the user to paginate through time windows. This caps the maximum data transfer per request.
- Use **server-side downsampling**: for a 24-hour replay, return one state per minute (1,440 frames) not one per delta (200,000 frames). The user cannot perceive sub-second differences in a depth chart animation anyway.
- Send data in a **compact binary format** (e.g., MessagePack or a custom binary encoding of price levels) rather than verbose JSON. A depth chart frame is just an array of `[price, quantity]` pairs -- 4 bytes per pair instead of ~30 bytes in JSON.

**Warning signs:**
- Replay endpoint returns raw deltas instead of pre-processed orderbook states.
- No `max_time_range` or `interval` parameter on the replay request.
- Browser tab memory exceeds 200MB during replay of a single market.
- Users on mobile or older laptops report page crashes during replay.
- The response payload for a 1-hour replay exceeds 2MB.

**Phase to address:**
First phase (Replay API) -- the data transfer strategy must be decided before any frontend rendering code is written. Choosing wrong means either a rewrite of the endpoint or a permanently sluggish visualization.

---

### Pitfall 2: Market Coverage Queries Scanning All Partitions, Killing Response Times

**What goes wrong:**
The market coverage dashboard needs to show, for each market: earliest data, latest data, snapshot count, delta count, and data completeness percentage. The existing `GET /markets` endpoint (in `src/api/routes/markets.py`) already does this with correlated subqueries:

```sql
SELECT m.ticker, m.title,
  (SELECT MIN(captured_at) FROM snapshots WHERE market_ticker = m.ticker) AS first_data_at,
  (SELECT MAX(ts) FROM deltas WHERE market_ticker = m.ticker) AS last_data_at
FROM markets m
```

This query touches every partition of both the `snapshots` table (monthly partitions) and the `deltas` table (daily partitions). With the system running since February 2026, by month 6 there will be ~4 monthly snapshot partitions and ~120+ daily delta partitions. PostgreSQL must scan the index of EVERY partition to compute `MIN()` and `MAX()` because it cannot prune partitions -- the query needs the global minimum/maximum, not a value from a known time range. The planner's cost grows linearly with partition count. At 120 partitions, the planning time alone can exceed 10-50ms per subquery, and with N markets, you get `N * 2 * planning_overhead` which becomes seconds for hundreds of markets.

The delta count (`SELECT COUNT(*) FROM deltas WHERE market_ticker = $1`) is even worse: `COUNT(*)` requires touching every qualifying row across all partitions. For a market with 500K deltas spread across 60 daily partitions, this is a full index scan of 60 partition indexes.

**Why it happens:**
PostgreSQL partition pruning only works when the query's WHERE clause contains the partition key (for deltas, that is `ts`). Queries filtered only on `market_ticker` cannot prune any partitions -- the planner must check all of them. The `idx_deltas_ticker_ts` index exists on each partition but does not help with `COUNT(*)` which still scans each partition's index segment for that ticker. The system was designed for single-market, time-bounded queries (`/orderbook` at a timestamp, `/deltas` in a time range) which partition-prune excellently, but cross-partition aggregation was not a design goal.

**How to avoid:**
- **Materialized coverage table**: Create a `market_coverage` table (or materialized view) that stores pre-computed per-market statistics: `ticker, first_data_at, last_data_at, snapshot_count, delta_count, last_updated`. Refresh it via a background job (cron every 5 minutes or triggered on each writer flush). The coverage dashboard reads from this table -- zero partition scanning.
- **Incremental updates**: Instead of full recomputation, update coverage stats incrementally. When the `DatabaseWriter` flushes deltas, also update `market_coverage.last_data_at` and increment `delta_count`. This is O(1) per flush, not O(partitions) per query.
- **Never run `COUNT(*)` across partitions at request time**. The existing `/markets/{ticker}` endpoint does exactly this (`SELECT COUNT(*) FROM deltas WHERE market_ticker = $1`) and it will degrade as data grows. Replace with the pre-computed count from the coverage table.
- **Partition the coverage query if you must compute live**: If a materialized table is not ready in time, at minimum add a time bound to coverage queries: `WHERE ts >= now() - interval '7 days'` so the planner only touches recent partitions. Show approximate counts with `~` prefix rather than exact counts.

**Warning signs:**
- `GET /markets` response time exceeds 500ms.
- `GET /markets/{ticker}` response time exceeds 200ms for markets with many deltas.
- EXPLAIN ANALYZE shows sequential scans across 50+ partitions.
- Database CPU spikes when the coverage dashboard loads.
- Users see a loading spinner for 3+ seconds on the markets page.

**Phase to address:**
Market Coverage phase -- this must be implemented BEFORE the coverage dashboard is built. Building the dashboard first with the existing slow queries, then trying to optimize later, means reworking the data layer under a live feature.

---

### Pitfall 3: Replay Visualization Rendering Every Frame, Freezing the Browser

**What goes wrong:**
The depth chart animation needs to render orderbook states over time -- visually showing how bid/ask levels change. The naive implementation sets up a `setInterval` or `requestAnimationFrame` loop that redraws the entire depth chart (SVG or Canvas area chart) for every frame of the replay. Each frame involves: (1) updating the yes/no level arrays, (2) recomputing the cumulative depth curves (sum quantities from best price outward), (3) rendering ~50-100 SVG path segments or Canvas draw calls for each side. At 30fps, this is 60 curve recomputations and 3,000+ draw operations per second. The JavaScript main thread blocks, mouse events stop being processed, the play/pause button becomes unresponsive, and the page appears frozen.

**Why it happens:**
Financial visualization libraries (Lightweight Charts, amCharts, etc.) are designed for time series data -- price over time on an X axis. Depth charts are fundamentally different: they show price on X and cumulative quantity on Y, updating the entire curve shape with each tick. There is no off-the-shelf React component for animated depth chart replay. Developers either (a) misuse a time-series library and get the wrong chart type, or (b) build a custom SVG depth chart that re-renders the entire React component tree on every state update, triggering expensive DOM reconciliation 30 times per second.

The existing `OrderbookPreview` component (in `dashboard/src/components/playground/orderbook-preview.tsx`) renders a static table of price levels. Upgrading this to an animated depth chart is a fundamentally different rendering problem.

**How to avoid:**
- Use **HTML5 Canvas**, not SVG, for the depth chart. Canvas is imperative -- you draw directly to a bitmap, no DOM reconciliation. For 30fps animation with 100+ data points per side, Canvas is 10-100x faster than React-managed SVG.
- **Separate the render loop from React's component lifecycle**. Use a `useRef` for the Canvas element and a standalone `requestAnimationFrame` loop that reads from a mutable data source (e.g., a `useRef` holding the current frame data). React never re-renders the canvas component itself -- only the controls (play/pause, timeline slider) are React-managed.
- **Pre-compute cumulative depth curves** during data loading, not during rendering. When the replay data arrives, immediately compute the cumulative sum for each frame's yes/no sides and store the results. During animation, the render loop just draws pre-computed curves -- no math per frame.
- **Throttle visual updates** to the monitor's refresh rate (typically 60fps). Even if the replay has one orderbook state per second covering a 1-hour period (3,600 states), the playback speed might be 60x, meaning 60 states per second -- perfectly aligned with `requestAnimationFrame`. But do NOT try to render 200,000 states at 60fps.
- **Use `OffscreenCanvas`** in a Web Worker for the depth chart rendering if the main thread is still too busy (e.g., because other dashboard components are updating). This keeps the UI responsive.

**Warning signs:**
- Depth chart component re-renders via React state updates on every frame.
- SVG elements with hundreds of `<path>` or `<rect>` elements being added/removed on each tick.
- Frame rate drops below 15fps during replay playback.
- Browser DevTools shows "Long Task" warnings exceeding 50ms.
- Play/pause button has perceptible delay (>200ms) when clicked during active replay.

**Phase to address:**
Replay Visualization phase -- the rendering architecture (Canvas vs SVG, React lifecycle management) must be decided at component design time. Switching from SVG to Canvas after building the component requires a complete rewrite.

---

### Pitfall 4: Playground Demo Data Burning Real User Credits

**What goes wrong:**
The playground's "Try an example" feature needs to populate with real captured market data so new users see a working orderbook. The current implementation (see TODO `2026-02-17-pre-populate-playground-with-real-captured-market-data.md`) hardcodes a ticker and timestamp, and when the user clicks "Send Request," it makes a real API call via their API key, deducting 5 credits (the `require_credits(5)` dependency on the `/orderbook` endpoint). A new free-tier user with 1,000 credits who clicks "Try an example" 5 times during exploration burns 25 credits -- 2.5% of their monthly allowance -- just trying to understand what the product does. Worse, if the playground adds replay visualization that internally makes multiple API calls (snapshot + N delta pages), a single "try the replay demo" could cost 50-100+ credits.

**Why it happens:**
The existing billing system (in `src/api/deps.py`) applies credit deduction uniformly through the `require_credits()` dependency. There is no concept of a "demo mode" or "sandbox request" -- every API call through the playground is a real, billed API call. This was acceptable when the playground only had a single endpoint, but with replay (which makes many internal calls) and a curated demo experience, the credit cost of exploration becomes a conversion-killing friction point.

**How to avoid:**
- **Pre-bake demo responses**: For the "Try an example" feature, store the response JSON server-side (e.g., a static JSON file in the Next.js `public/` directory or a cached API response). When the user clicks "Try an example," serve the pre-baked response directly -- zero API calls, zero credit cost. The response should be clearly labeled as "Sample data" to avoid confusion.
- **Dedicated demo endpoint**: Create an unauthenticated `GET /demo/orderbook` endpoint that returns a curated orderbook response from a real market at a known-good timestamp. This endpoint is not metered, not authenticated, and returns a fixed response. Limit it to specific pre-selected market/timestamp pairs.
- **For replay demo**: Pre-compute a full replay sequence for one curated market and serve it as a static asset. A 5-minute replay at 1-second intervals is only 300 frames of data -- compresses to ~50KB. Load this directly in the browser without any API calls.
- **Free demo credits**: If real API calls must be used for demos, add a separate `demo_credits` field to `billing_accounts` that is deducted first for playground requests originating from the dashboard. These credits do not count toward the monthly limit and are not PAYG-billed. This is the most complex solution and should be avoided if pre-baked responses suffice.
- **Flag playground requests**: Add a `X-Playground: true` header from the Next.js proxy. The billing middleware can track playground usage separately and potentially exempt it, or at minimum report it so you can see how many credits users burn on exploration vs. production use.

**Warning signs:**
- New users exhaust free credits within their first session without making a single production API call.
- Users sign up, try the playground once, see credits deducted, and never return.
- Analytics show high playground usage correlating with high churn among free-tier users.
- Replay demo costs 50+ credits per "try it" click.

**Phase to address:**
Playground Data Population phase -- must be solved before adding replay to the playground. The replay demo's credit cost amplifies this problem by 10-50x compared to the single-request playground.

---

### Pitfall 5: Archived Data Invisible to Coverage Dashboard

**What goes wrong:**
The archival system (`src/collector/archival.py`) moves old deltas and snapshots from PostgreSQL to Parquet files in Supabase Storage, then DROPS the source partitions. After archival runs, `SELECT MIN(captured_at) FROM snapshots WHERE market_ticker = $1` no longer finds the oldest data -- it only sees data that is still in hot storage. The coverage dashboard shows `first_data_at: 2026-02-11` (when archival ran) instead of `first_data_at: 2026-02-13` (when collection actually started). Worse, `delta_count` drops by thousands overnight when archival removes old partitions. Users see their data coverage "shrinking" and file support tickets thinking data was lost.

**Why it happens:**
The archival system and the coverage dashboard operate on different data stores. Archival removes data from PostgreSQL and puts it in Supabase Storage (Parquet files). The coverage queries only read PostgreSQL. There is no metadata layer that tracks "this market has data from date X to date Y across both hot and cold storage." The `market_coverage` table (if built) only reflects hot storage unless explicitly designed to include archived ranges.

**How to avoid:**
- **Track archival boundaries in the coverage table**: When archival runs, update `market_coverage.archived_through` to record the latest date that was archived. The coverage dashboard shows `first_data_at` as the minimum of `archived_first_data_at` and the hot storage's `MIN(captured_at)`.
- **Write archival metadata before deleting**: Before the `_delete_archived_data()` method drops a partition, write a record to an `archive_inventory` table: `(market_ticker, date, delta_count, snapshot_count, parquet_path)`. The coverage dashboard can aggregate from this table for dates before the archival cutoff.
- **Alternatively, never drop coverage metadata**: The `first_data_at` and `last_data_at` for a market should be stored in the `markets` table itself (or a coverage table) and NEVER recomputed from the source data. Update these columns on write, not on read. Archival does not touch them.
- **Test with archival running**: Any coverage dashboard test must include a scenario where archival has run and removed historical data. If the dashboard only works with all data in hot storage, it will break in production within `hot_storage_days` (default: likely 7-14 days).

**Warning signs:**
- Coverage dashboard shows different `first_data_at` before and after archival runs.
- `delta_count` for a market decreases overnight.
- Users ask "why did my data coverage date change?"
- Coverage dashboard shows zero data for markets that have only archived data.

**Phase to address:**
Market Coverage phase -- the archival-awareness must be designed into the coverage data model from the start. Retrofitting it after users have seen (and relied on) "incorrect" coverage dates requires a migration and erodes trust.

---

### Pitfall 6: N+1 Query Pattern in Coverage Dashboard

**What goes wrong:**
The coverage dashboard shows a grid/table of all markets with their coverage statistics. The naive implementation fetches the market list, then for each market individually queries snapshot count, delta count, first/last data timestamps, and data completeness. With 500+ tracked markets (the discovery system has `max_subscriptions: 1000`), this generates 500+ individual database queries per page load. Each query takes 5-20ms (partition scanning), totaling 2.5-10 seconds of pure database time before the page can render.

The existing `GET /markets` endpoint already shows this pattern: correlated subqueries run for each row in the `markets` table. As the markets count grows from tens to hundreds, this endpoint will linearly slow down.

**Why it happens:**
The correlated subquery pattern in `GET /markets` was fine when there were 20-30 markets. It is a natural way to write the query -- "for each market, find its data range." But correlated subqueries execute per row, and each subquery hits partitioned tables. The compound cost is `markets * partitions * index_scans`. Developers test with 10 markets and never see the problem.

**How to avoid:**
- **Pre-computed coverage table** (same solution as Pitfall 2): Eliminate the correlated subqueries entirely. The coverage dashboard reads from `market_coverage` which has one row per market with all statistics pre-computed.
- **If computing live, use set-based aggregation**: Replace correlated subqueries with JOINs to pre-aggregated CTEs:
  ```sql
  WITH delta_stats AS (
    SELECT market_ticker, MIN(ts) AS first_delta, MAX(ts) AS last_delta, COUNT(*) AS delta_count
    FROM deltas
    WHERE ts >= now() - interval '7 days'  -- Bounded time range for partition pruning!
    GROUP BY market_ticker
  ),
  snapshot_stats AS (
    SELECT market_ticker, MIN(captured_at) AS first_snapshot, COUNT(*) AS snapshot_count
    FROM snapshots
    GROUP BY market_ticker
  )
  SELECT m.ticker, d.*, s.*
  FROM markets m
  LEFT JOIN delta_stats d ON d.market_ticker = m.ticker
  LEFT JOIN snapshot_stats s ON s.market_ticker = m.ticker
  ```
  This scans each partition once (not once per market) and groups results. With `enable_partitionwise_aggregate = on`, PostgreSQL can aggregate within each partition and merge results.
- **Add pagination to the coverage endpoint**: Do not return all 500+ markets in one response. Paginate with 50 markets per page, allowing the database to handle smaller result sets.

**Warning signs:**
- Database connection pool exhaustion during coverage page loads (20 connections used for one request).
- EXPLAIN ANALYZE shows "Loops: 500" on subquery nodes.
- Coverage page response time grows linearly with market count.
- `pg_stat_activity` shows dozens of concurrent queries from a single HTTP request.

**Phase to address:**
Market Coverage phase -- the query pattern must be set-based or pre-computed from the outset. Fixing N+1 after launch means rewriting the coverage API, the database queries, and potentially adding a background job system.

---

### Pitfall 7: Replay Playback Controls That Ignore Browser Tab Visibility

**What goes wrong:**
The replay visualization has a "play" button that animates the depth chart over time. When the user switches to another browser tab, `requestAnimationFrame` stops firing (browsers throttle background tabs). But if the replay uses `setInterval` or tracks elapsed wall-clock time, it keeps "playing" in the background -- when the user switches back, the chart jumps forward by the elapsed time, skipping all the intermediate frames. The user sees a jarring discontinuity. Alternatively, if the timer accumulates while paused, the replay tries to "catch up" by rendering hundreds of frames rapidly when the tab regains focus, freezing the browser.

**Why it happens:**
`requestAnimationFrame` is designed for visual rendering and correctly pauses when the tab is hidden. But developers often combine it with `Date.now()` to calculate delta-time for animation progress, creating a mismatch: the animation frame fires once when the tab becomes visible again, but `Date.now() - lastFrameTime` returns a large value (seconds or minutes), causing the playback position to leap forward.

**How to avoid:**
- Use **frame-counting**, not wall-clock time, for replay progress. Each `requestAnimationFrame` callback advances the replay by exactly one frame/step regardless of how much real time has passed. This naturally pauses when the tab is hidden.
- Implement the `document.visibilitychange` event listener. When the tab becomes hidden, auto-pause the replay. When it becomes visible, resume from the last rendered frame (not from where it "would have been").
- Store the **current frame index** as the authoritative playback position. The timeline scrubber, play/pause state, and rendering loop all reference this single value. Wall clock time is never used for replay progress.
- Allow **adjustable playback speed** (1x, 2x, 5x, 10x) where speed is "frames per requestAnimationFrame callback," not "real-time-to-replay-time ratio."

**Warning signs:**
- Replay jumps forward when returning to the tab.
- Browser freezes momentarily when switching back to the tab during replay.
- Replay position does not match the timeline scrubber after tab-switching.
- Replay at "1x speed" runs faster on a 120Hz monitor than a 60Hz monitor (indicating coupling to `requestAnimationFrame` rate without normalization).

**Phase to address:**
Replay Visualization phase -- the playback controller architecture must handle tab visibility from the initial implementation. This is not a polish item -- it affects the core animation loop design.

---

### Pitfall 8: Coverage Completeness Metric That Lies About Data Quality

**What goes wrong:**
The coverage dashboard shows a "completeness" percentage for each market -- intending to answer "how much of this market's trading life do we have data for?" The naive calculation is `(last_data - first_data) / (market_close - market_open) * 100`. But this ignores sequence gaps (recorded in the `sequence_gaps` table), overnight periods with no trading, and archival boundaries. A market that was actively collected for 23 out of 24 hours but had a 1-hour gap during peak trading shows 95.8% completeness -- but the missing hour might be the most valuable data. The user trusts the high percentage and builds a backtest, only to discover missing data at critical moments.

**Why it happens:**
"Completeness" is harder to define than it appears. The collector records sequence gaps (`sequence_gaps` table) when it detects missing sequences, and these gaps trigger resubscription. But the gap records tell you WHEN a gap occurred, not how much data was lost (the gap size is `received_seq - expected_seq` which is in sequence numbers, not time duration). Converting sequence gaps to time-based coverage holes requires knowing the typical delta rate for that market, which varies by time of day and market activity.

**How to avoid:**
- **Do not show a single completeness percentage**. Instead, show a **timeline heatmap**: a horizontal bar per market where each hour/day is colored (green = data, red = gap, gray = no trading). This gives users a visual sense of coverage without a misleading number.
- **If you must show a number**, define it precisely: "Percentage of 1-minute intervals within the data range that contain at least one delta." This is computable from the deltas table: `SELECT COUNT(DISTINCT date_trunc('minute', ts)) FROM deltas WHERE market_ticker = $1 AND ts BETWEEN $2 AND $3`, divided by total minutes in the range.
- **Surface gap information explicitly**: Show the `sequence_gaps` count per market in the coverage view. "3 sequence gaps detected" is more honest than "99.2% complete."
- **Distinguish between "no data" and "no activity"**: Some markets have legitimate zero-activity periods (overnight, weekends for non-crypto). The coverage metric should exclude these periods. Cross-reference with Kalshi market schedules or use the trades table as a proxy for "market was active."
- Pre-compute the minute-level coverage in the background job, not at query time. Scanning deltas for `COUNT(DISTINCT date_trunc('minute', ts))` across all partitions is expensive.

**Warning signs:**
- Coverage shows 100% for markets with known gaps.
- Users build backtests and find missing data periods that the dashboard did not flag.
- Coverage percentage is expensive to compute (>500ms query).
- No reference to the `sequence_gaps` table in the coverage logic.

**Phase to address:**
Market Coverage phase -- the completeness metric design is a product decision that affects both the API response schema and the dashboard UI. Get the definition right before building the aggregation query.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Serving replay data as one giant JSON response | Simple implementation, works for small replays | Browser OOM for large replays, no progressive rendering, cache-unfriendly | Never -- streaming or chunked delivery should be the default |
| Computing coverage stats via live queries on partitioned tables | No new tables or background jobs needed | O(partitions * markets) query cost, coverage page becomes unusable at 100+ markets * 30+ partitions | Only as an initial prototype with <20 markets, must be replaced before any real traffic |
| Using SVG for depth chart animation | Familiar React rendering, easy tooltips and hover states | Re-renders trigger DOM reconciliation, frame rate drops below 15fps at 100+ price levels | Acceptable for static (non-animated) depth chart preview only |
| Hardcoding demo market ticker in playground | Ships fast, no infrastructure needed | Ticker expires when market settles, playground breaks for new users | Only until dynamic example selection is built -- must have a fallback mechanism |
| Using the same API endpoint for playground demos and production requests | No code duplication, billing logic stays consistent | Demo exploration costs real credits, discouraging new users from experimenting | Never for replay demos (too expensive). Acceptable for single-endpoint demos only with clear credit cost disclosure |
| Storing replay animation state in React useState | Familiar React pattern | 30-60 state updates per second trigger re-renders of the component tree, causing frame drops | Never for the animation loop -- use refs and imperative Canvas updates |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Archival system + Coverage dashboard | Coverage queries only check hot storage (PostgreSQL), ignoring archived data in Supabase Storage | Track archival boundaries in a metadata table. `first_data_at` should reflect the earliest available data across both hot and cold storage |
| Billing system + Playground demos | Playground requests go through `require_credits()` just like production API calls | Pre-bake demo responses as static JSON or create a zero-cost demo endpoint. Replay demos should NEVER use live API calls |
| Daily-partitioned deltas + Coverage aggregation | Running `COUNT(*)` or `MIN/MAX` across all partitions without time bounds | Always bound coverage queries with a time range for partition pruning, or use pre-computed statistics in a `market_coverage` table |
| Existing orderbook reconstruction + Replay | Calling `reconstruct_orderbook()` N times to generate N replay frames | Build a streaming reconstruction function that processes deltas incrementally, yielding states at intervals, using a single database query for the delta range |
| Next.js App Router + SSE streaming | Using `pages/api/` (Pages Router) for streaming endpoints, which buffers responses | Use Route Handlers in `app/api/` with `ReadableStream` for true streaming. The dashboard already uses App Router |
| Canvas rendering + React lifecycle | Calling `setState` to trigger re-renders for each animation frame | Use `useRef` for canvas element and data, manage the animation loop outside React's render cycle with `requestAnimationFrame` |
| Sequence gaps table + Coverage completeness | Ignoring gap records when computing data completeness | Cross-reference `sequence_gaps` with delta timestamps to identify actual coverage holes, not just sequence number discontinuities |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Live `COUNT(*)` on partitioned deltas table per market | Coverage page loads in 3-10+ seconds | Pre-computed `market_coverage` table updated by background job | >50 markets * >30 daily partitions (~50 days of data) |
| Correlated subqueries in `GET /markets` (existing code) | Linear slowdown with market count, each subquery scans all partitions | Replace with CTE-based set aggregation or materialized view | >100 markets, already slow at 50+ with many partitions |
| Full JSON response for replay data (no streaming) | Browser hangs parsing large JSON, no progressive rendering | SSE streaming or chunked transfer, send replay frames incrementally | >5MB response (~1 hour of active market replay data) |
| SVG depth chart with React re-renders at 30fps | Frame drops, unresponsive UI, Chrome DevTools "Long Task" warnings | Canvas rendering with imperative draw loop, outside React lifecycle | >50 price levels per side, always breaks at animation speed |
| No index on `market_coverage.ticker` (new table) | Full table scan on every coverage lookup, O(markets) per request | Create unique index on `(ticker)` at table creation time | >100 markets, immediately noticeable without index |
| Loading all replay frames into browser memory before starting playback | High time-to-first-frame, memory spike at load, no feedback during loading | Stream frames and start playback after first batch arrives, buffer ahead of playback position | >1,000 replay frames (>15 minutes at 1-frame-per-second resolution) |
| `requestAnimationFrame` loop computing cumulative depth on every frame | CPU-bound main thread, janky animations | Pre-compute cumulative depth curves during data loading, render loop only draws | >100 price levels per side, noticeable at >30fps |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Demo endpoint returning data for ANY market/timestamp without authentication | Unauthenticated data exfiltration -- competitors scrape full orderbook history for free via the demo endpoint | Demo endpoint only serves pre-selected, curated market/timestamp pairs. Do not accept arbitrary tickers or timestamps on unauthenticated endpoints |
| Replay endpoint returning unlimited time ranges without rate limiting | Single API key can scrape months of data rapidly by requesting maximum time ranges | Enforce `max_time_range` per request (e.g., 4 hours), add per-key rate limiting on replay endpoint (e.g., 10 replay requests per minute), credit cost proportional to time range |
| Coverage dashboard exposing internal metadata (gap counts, archival dates) to unauthorized users | Competitors learn your data collection schedule, gap patterns, and coverage weaknesses | Coverage data should require authentication. The public view shows only "data available: yes/no" and rough date ranges, not precise gap information or delta counts |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Replay visualization with no timeline scrubber | User can only watch linearly, cannot skip to interesting moments, cannot pause and inspect a specific state | Full timeline scrubber with click-to-seek, play/pause, speed control (1x/2x/5x/10x), and frame-by-frame step buttons |
| Coverage dashboard showing only raw numbers (snapshot_count: 4521) | Numbers are meaningless without context -- is 4521 snapshots a lot? | Show visual timeline coverage bar, color-coded by data density. Show relative metrics: "12 hours of data at ~10 snapshots/hour" |
| Loading replay data with no progress indicator | User clicks "replay" and sees nothing for 3-5 seconds while data loads, thinks the feature is broken | Show a progress bar during data loading ("Loading orderbook history... 45%"). Start rendering as soon as first frames arrive (progressive loading) |
| Depth chart with no price axis labels or quantity tooltips | User sees colored areas but cannot read actual prices or quantities | Clear axis labels: price in cents on X-axis, cumulative quantity on Y-axis. Hover tooltips showing exact price/quantity at cursor position |
| Coverage page showing all markets in a flat list with no filtering | User with 500+ markets cannot find the one they care about | Search/filter by ticker, event, category, status. Sort by coverage date range, delta count, or data freshness. Default sort: most recently active first |
| Playground "Try an example" that does not work because the market settled | New user's first experience is an error message | Dynamic example selection: query for a market with recent data that is still active. Fallback to pre-baked static response if no live market is suitable |

## "Looks Done But Isn't" Checklist

- [ ] **Replay endpoint:** Often missing `max_time_range` parameter -- verify that requesting a 30-day replay returns a 400 error, not a 10-minute hang followed by OOM
- [ ] **Replay endpoint:** Often missing interval/downsampling -- verify that a 4-hour replay returns ~240 frames (1/min), not 100,000+ raw delta states
- [ ] **Coverage table:** Often missing archival-awareness -- verify that coverage stats are the same before and after `archival.py` runs
- [ ] **Coverage table:** Often missing background refresh -- verify that newly collected data appears in coverage within 5 minutes without a page refresh
- [ ] **Depth chart animation:** Often missing Canvas rendering -- verify frame rate stays above 30fps with 99 yes levels + 99 no levels animating
- [ ] **Depth chart animation:** Often missing tab visibility handling -- verify that switching away and back does not cause a time jump or freeze
- [ ] **Demo data:** Often missing credit-free path -- verify that "Try an example" in the playground costs 0 credits
- [ ] **Demo data:** Often missing fallback for settled markets -- verify that the demo still works after the example market settles
- [ ] **Coverage completeness:** Often missing gap awareness -- verify that a market with known sequence gaps shows those gaps in the coverage view
- [ ] **Replay controls:** Often missing keyboard shortcuts -- verify Space (play/pause), Arrow keys (frame step), and +/- (speed) work during replay
- [ ] **Coverage dashboard:** Often missing pagination -- verify that loading 500+ markets does not produce a >2-second response time

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Browser OOM from unbounded replay data | MEDIUM | Add `max_time_range` and streaming to the endpoint. Frontend code that expects a single JSON response must change to handle streamed data. Not a breaking API change if the replay endpoint was not yet public |
| Coverage queries scanning all partitions | LOW | Create `market_coverage` table and populate from existing data with a one-time migration. Swap the API endpoint to read from it. Can be done without any frontend changes if the response schema is kept the same |
| SVG depth chart freezing browser | HIGH | Complete rewrite from SVG React component to Canvas imperative rendering. No code reuse possible. All interaction handlers (hover, click, tooltips) must be reimplemented for Canvas |
| Demo data burning credits | LOW | Replace live API calls with pre-baked static responses. No database migration needed. Dashboard-only change |
| Archived data invisible to coverage | MEDIUM | Backfill `market_coverage` table from archive inventory. Write a one-time script to scan Parquet files in Supabase Storage and reconstruct historical coverage. Ongoing fix: update archival code to maintain coverage metadata |
| N+1 query in coverage endpoint | LOW | Replace correlated subqueries with CTE-based aggregation. Pure SQL change, no API schema change. Alternatively, switch to pre-computed coverage table |
| Replay tab-switching bug | LOW | Add `visibilitychange` listener and switch to frame-counting. Localized fix in the playback controller, does not affect other components |
| Misleading completeness percentage | LOW | Replace single number with timeline heatmap visualization. UI change only, does not affect API. Can be done incrementally alongside the existing metric |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Browser memory explosion (unbounded replay) | Replay API | Load test: request a 4-hour replay for an active market. Verify response is streamed (chunked transfer), total payload <5MB, browser memory delta <50MB |
| Coverage queries scanning all partitions | Market Coverage | EXPLAIN ANALYZE the coverage endpoint query with 100+ markets and 60+ daily partitions. Verify no sequential scans across all partitions. Total query time <100ms |
| Depth chart freezing browser | Replay Visualization | Profile rendering with Chrome DevTools Performance panel during 60fps playback with 99 yes + 99 no levels. Verify no frame exceeds 16ms (60fps target) |
| Playground demo burning credits | Playground Data | Verify "Try an example" produces a response with `credits_cost: 0` in the response metadata. Check billing_accounts shows no credit deduction for demo requests |
| Archived data invisible to coverage | Market Coverage | Run `archival.py` for dates with data. Verify `GET /markets` still shows correct `first_data_at` including pre-archival dates |
| N+1 query in coverage dashboard | Market Coverage | Load test `GET /markets` with 500 markets. Verify `pg_stat_statements` shows 1-3 queries executed, not 500+. Response time <500ms |
| Replay tab visibility bug | Replay Visualization | Open replay, switch to another tab for 30 seconds, switch back. Verify replay resumes from the last displayed frame, not 30 seconds ahead |
| Misleading completeness metric | Market Coverage | Create test market with a known 1-hour gap. Verify coverage view clearly shows the gap visually and numerically, not just "95% complete" |

## Sources

- [PostgreSQL Documentation: Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html) -- Partition pruning behavior, `enable_partitionwise_aggregate`, planning time growth with partition count (HIGH confidence)
- [PostgresAI: How Does Planning Time Depend on Number of Partitions](https://postgres.ai/blog/20241003-how-does-planning-time-depend-on-number-of-partitions) -- Quantified planning time growth: 12ms at 1000 partitions (HIGH confidence)
- [pganalyze: Partition-wise Joins and Aggregates](https://pganalyze.com/blog/5mins-postgres-partition-wise-joins-aggregates-query-performance) -- `enable_partitionwise_aggregate` disabled by default due to CPU/memory cost (HIGH confidence)
- [CYBERTEC: Killing Performance with PostgreSQL Partitioning](https://www.cybertec-postgresql.com/en/killing-performance-with-postgresql-partitioning/) -- Cross-partition aggregate performance pitfalls (HIGH confidence)
- [Zigpoll: Frontend Data Visualization Optimization](https://www.zigpoll.com/content/how-can-we-optimize-the-frontend-data-visualization-components-to-handle-largescale-realtime-datasets-without-compromising-performance-or-user-experience) -- LTTB downsampling, rolling window, DOM batching, incremental updates (MEDIUM confidence)
- [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) -- Canvas 2D rendering (not WebGL), performant with thousands of bars, React integration patterns (HIGH confidence)
- [CoinAPI: Crypto Order Book Replay Guide](https://www.coinapi.io/blog/crypto-order-book-replay) -- Snapshot + diff replay, sequence-aligned reconstruction (MEDIUM confidence)
- [Nordic APIs: API Sandbox Best Practices](https://nordicapis.com/7-best-practices-for-api-sandboxes/) -- Free sandbox credits, authentication in sandbox, usage monitoring (MEDIUM confidence)
- [Plaid Sandbox Documentation](https://plaid.com/docs/sandbox/) -- Industry pattern for free demo/sandbox environments separate from production billing (HIGH confidence)
- [Next.js Streaming Documentation](https://nextjs.org/docs/14/app/building-your-application/routing/loading-ui-and-streaming) -- App Router streaming with ReadableStream, progressive rendering (HIGH confidence)
- [HackerNoon: Streaming in Next.js 15](https://hackernoon.com/streaming-in-nextjs-15-websockets-vs-server-sent-events) -- SSE vs WebSocket for Next.js streaming use cases (MEDIUM confidence)
- KalshiBook codebase analysis: `src/api/services/reconstruction.py`, `src/api/routes/markets.py`, `src/api/routes/orderbook.py`, `src/api/deps.py`, `src/api/services/billing.py`, `src/collector/writer.py`, `src/collector/archival.py`, `supabase/migrations/`, `dashboard/src/components/playground/` (HIGH confidence, direct codebase inspection)

---
*Pitfalls research for: Discovery, Replay & Coverage Features for KalshiBook*
*Researched: 2026-02-18*
