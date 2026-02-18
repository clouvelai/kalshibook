# Project Research Summary

**Project:** KalshiBook Discovery & Replay (v1.2)
**Domain:** Prediction market L2 orderbook data API — visualization, discovery, and replay features
**Researched:** 2026-02-18
**Confidence:** HIGH

## Executive Summary

KalshiBook is adding three new capability clusters to an existing FastAPI + Next.js SaaS dashboard: market data discovery (a browsable, filterable table of what data exists and how much), orderbook replay visualization (the signature feature — animated depth chart with timeline scrubber showing orderbook evolution over time), and playground upgrades (real ticker autocomplete, dynamic examples, multi-endpoint support). The existing stack is solid and nearly complete — only two new frontend dependencies are needed (Recharts via `shadcn add chart`, and date-fns). The backend requires no new packages, only new service/route modules and one Postgres materialized view. All four research areas converge on the same build order: coverage data infrastructure first, then playground UX, then replay visualization.

The recommended architecture uses server-side incremental reconstruction for replay (one database scan for all deltas, emit frames at target timestamps — not N independent reconstructions), a materialized view for coverage stats (pre-computed, refreshed every 5-15 minutes), and browser-side Canvas rendering for the animated depth chart (not React-managed SVG). Dashboard-internal endpoints for playground examples and market search use Supabase JWT auth with no credit deduction, keeping exploration free for users. These three decisions are non-negotiable: getting any of them wrong results in either a rewrite (SVG to Canvas is a full rewrite) or a permanently degraded product (coverage page timing out at scale, or users burning credits on demos and churning).

The main risks are performance-related, not technical uncertainty. The existing codebase already has `reconstruction.py` (Python), the daily-partitioned tables, and the credit billing system — none of this is novel territory. The danger is in naive implementations: correlated subqueries per market on partitioned tables (O(markets x partitions) query cost), per-frame API calls for replay (300 credits per replay session), SVG area charts re-rendering through React state on every animation frame (browser freeze at 30fps with 99 price levels). Every pitfall has a clear prevention strategy documented in PITFALLS.md — the phase ordering below is specifically designed to address these in the right sequence.

---

## Key Findings

### Recommended Stack

The existing stack (React 19.1 / Next.js 15.5 / FastAPI / asyncpg / Supabase Postgres / shadcn / TanStack Table / radix-ui) handles everything except charting and date formatting. Only two new packages are needed on the frontend. The backend needs zero new Python packages.

**Core new technologies:**
- **Recharts 3.7 (via `shadcn add chart`):** Depth chart + price overlay — integrates natively with shadcn's design system, React JSX pattern, zero new abstraction to learn. Requires `react-is` override for React 19 compatibility.
- **date-fns 4.x:** Timestamp formatting and date range calculations — tree-shakable, functional API, ~2-5KB actual bundle impact.
- **requestAnimationFrame + useRef (built-in):** Replay animation loop — increments a frame index at configurable speed. Not an animation library; this is data-driven playback.
- **Postgres materialized view (new database object):** Pre-computed coverage stats — eliminates O(partitions x markets) query cost on the coverage dashboard. Refresh with `CONCURRENTLY` for zero downtime.

**Critical version requirement:** Recharts 3.7+ requires `"overrides": { "react-is": "^19.0.0" }` in `dashboard/package.json` after running `shadcn add chart`.

Full details: `.planning/research/STACK.md`

### Expected Features

Research confirms a clear four-tier priority structure. The feature dependency tree mandates that market coverage listing be built before everything else — it is the foundation for playground autocomplete, examples, and replay market selection.

**Must have (table stakes):**
- Market coverage table with filters, search, sort — users cannot discover data without this
- Data completeness indicator per market — needed for trust (gap-aware, not a naive percentage)
- Market ticker autocomplete in playground — broken workflow without this; users cannot guess tickers like `KXBTC-25FEB14-T96074.99`
- Populated playground examples from real data — current hardcoded example breaks when market settles
- Static depth chart visualization — any orderbook data platform shows visual depth; raw table is insufficient

**Should have (competitive differentiators):**
- Animated orderbook replay with timeline scrubber — no prediction market data provider offers this; SteelEye charges enterprise pricing for traditional markets
- Calendar heatmap of data coverage (requires new `GET /coverage/{ticker}` backend endpoint for per-day density)
- Multi-endpoint playground support (all 10 endpoints, not just orderbook)

**Defer (v2+):**
- Real-time live orderbook visualization — requires WebSocket streaming infrastructure not yet built
- Price timeline overlay on replay — v1.3; build replay first, add sync'd candle chart later
- Comparison view (two markets side-by-side)
- Full-text search across market rules/descriptions
- Derived metrics (spread, imbalance, VWAP) — explicitly out of scope per PROJECT.md

Full details: `.planning/research/FEATURES.md`

### Architecture Approach

The new features integrate cleanly into the existing layered architecture (Next.js dashboard -> lib/api.ts fetchAPI -> FastAPI routes -> asyncpg -> Supabase Postgres). Three new route modules (coverage, replay, playground) and two new service modules (coverage, replay) are added. The existing `reconstruction.py` service is reused by the replay service — no duplication. The existing `key_usage_log` and billing infrastructure powers usage analytics with only an aggregation query change.

**Major new components:**
1. **`market_coverage_stats` materialized view (Postgres)** — pre-computes first/last data dates, snapshot/delta/trade counts per market; refreshed every 5-15 minutes; enables O(1) coverage page loads
2. **`POST /replay` endpoint + `replay.py` service** — server-side incremental reconstruction: one snapshot lookup + one delta range query + sequential walk emitting frames at N evenly-spaced timestamps; returns `{frames: [{ts, yes, no}, ...]}` as a single batch response
3. **`GET /playground/examples` + `GET /playground/search`** — dashboard-internal endpoints (Supabase JWT auth, no credit cost); returns curated example markets and ticker autocomplete results
4. **`OrderbookChart` (Canvas-based)** — imperative Canvas rendering with `requestAnimationFrame` loop outside React's lifecycle; `useReplay` hook manages frame index, play/pause, speed as refs (not state) for the animation loop
5. **Coverage page + CoverageTable** — reads from materialized view via `GET /coverage`; uses TanStack Table (already installed) for sortable/filterable market list

**Pattern enforcement:** Dashboard-internal endpoints use `get_authenticated_user` (Supabase JWT), not `require_credits`. Data endpoints remain unchanged. This is the architectural boundary between free exploration and billed API access.

Full details: `.planning/research/ARCHITECTURE.md`

### Critical Pitfalls

Eight pitfalls documented, all with HIGH confidence based on direct codebase analysis. The top five that must be solved before or during the relevant phase:

1. **Browser memory explosion from unbounded replay data** — A 24-hour active market replay can generate 200K+ deltas = 60MB parsed JSON. Prevention: dedicated replay endpoint with server-side downsampling (one orderbook state per configurable interval, default 1/minute for a 4-hour window = 240 frames max), hard `max_time_range` enforcement, response under 5MB. Must decide before any frontend code is written.

2. **Coverage queries scanning all partitions** — `SELECT COUNT(*), MIN(ts), MAX(ts)` across daily-partitioned deltas table per market = O(markets x partitions) cost. At 120+ partitions and 500+ markets, the coverage page times out. Prevention: materialized view pre-computed at write time, refreshed by background job. Must be built before the coverage dashboard.

3. **SVG depth chart freezing browser** — Re-rendering React SVG components (Recharts AreaChart) at 30fps with 99 price levels triggers DOM reconciliation 30 times per second -> browser freeze, unresponsive UI. Prevention: Canvas rendering with imperative `requestAnimationFrame` loop, `useRef` for mutable frame data, React manages only controls (play/pause, slider). No animation libraries. Must decide at component design time — SVG to Canvas is a full rewrite.

4. **Playground demo burning real user credits** — Current playground calls live API endpoints through `require_credits()`. Replay demo could cost 50-100+ credits per click -> new user churn. Prevention: pre-bake example responses as static JSON or serve from zero-cost dashboard-internal endpoint. Must be solved before replay is added to the playground.

5. **Archived data invisible to coverage** — `archival.py` drops old partitions; coverage queries only see hot storage -> `first_data_at` jumps forward after archival, users think data was lost. Prevention: store coverage metadata in `markets` table (or coverage table) updated on write, never recomputed from source tables. Archival process must update `archived_through` field. Must be designed into coverage data model from the start.

Full details: `.planning/research/PITFALLS.md`

---

## Implications for Roadmap

Based on combined research, suggest four phases with a strict dependency-respecting order.

### Phase 1: Coverage Data Infrastructure + Market Discovery

**Rationale:** Every other feature depends on this. Replay needs market selection (autocomplete comes from market list). Playground examples need markets with confirmed active data. The calendar heatmap needs the new coverage endpoint. More critically, the materialized view MUST exist before the coverage dashboard is built — building the UI first with live queries creates a slow feature that must be reworked under live traffic. The archived-data-visibility problem (Pitfall 5) must be designed into the data model here, not retrofitted later.

**Delivers:** Browsable market coverage table in the dashboard sidebar, market detail view, data completeness indicators (gap-aware, shown as timeline bars not a percentage), market grouping by event/series. Also delivers the materialized view and `GET /coverage` API that all subsequent phases use.

**Addresses (from FEATURES.md):** Market coverage listing (table stakes), data completeness badge (table stakes), market grouping by event (should-have)

**Implements (from ARCHITECTURE.md):** `market_coverage_stats` materialized view, `coverage.py` service + route, `CoverageTable`, `CoverageFilters`, `CoverageSummaryCards`, `useCoverage` hook, sidebar nav additions

**Avoids (from PITFALLS.md):** Pitfall 2 (partition scanning — materialized view), Pitfall 5 (archived data invisibility — metadata stored on write), Pitfall 6 (N+1 queries — set-based aggregation or materialized view), Pitfall 8 (misleading completeness — heatmap not percentage)

**Research flag:** Standard patterns — materialized views, TanStack Table, Supabase migrations are well-documented. No additional research phase needed.

---

### Phase 2: Playground Upgrade (Discovery UX)

**Rationale:** Playground is currently broken for new users (hardcoded ticker, no autocomplete, single endpoint). This phase transforms it from a developer demo into an interactive data explorer. It depends on Phase 1's coverage data for market search and valid example timestamps. It must solve the credit-burning problem (Pitfall 4) before replay is ever added to the playground — otherwise replay would amplify the problem 50x.

**Delivers:** Market ticker autocomplete (shadcn Command + Popover), dynamic examples from real data (zero credit cost), multi-endpoint support for all 10 API endpoints, timestamp auto-fill within data range for selected market, endpoint-specific response previews.

**Addresses (from FEATURES.md):** Ticker autocomplete (P1, table stakes), populated playground examples (P1), multi-endpoint playground (P2), timestamp auto-fill (P2)

**Implements (from ARCHITECTURE.md):** `GET /playground/examples` + `GET /playground/search` (JWT-authed, no credits), `MarketPicker` component, `ExampleCards` component, modifications to `use-playground.ts` and `playground-form.tsx`

**Avoids (from PITFALLS.md):** Pitfall 4 (demo data burning credits — pre-baked responses or zero-cost endpoint), UX pitfall "Try an example that doesn't work because the market settled"

**Research flag:** Standard patterns. shadcn Command/Combobox, FastAPI JWT auth, static response serving are all documented. No additional research phase needed.

---

### Phase 3: Orderbook Replay Visualization

**Rationale:** This is the signature differentiator — no prediction market data provider offers this. It is also the most complex phase and the one with the most pitfall exposure. Build order within this phase: (1) static depth chart component first — verify the visualization is correct before adding animation; (2) replay API backend with server-side incremental reconstruction — testable via curl before any frontend exists; (3) replay frontend with animation loop. The rendering architecture decision (Canvas, not SVG) must be made at design time — there is no incremental path from SVG to Canvas.

**Delivers:** Static depth chart component (Recharts AreaChart step interpolation for the static preview), replay API endpoint (batch frames, server-side incremental reconstruction), animated replay with requestAnimationFrame loop, timeline scrubber (Radix Slider), play/pause/speed controls, trade price marker overlay.

**Addresses (from FEATURES.md):** Static depth chart (P1, table stakes), animated replay (P1, differentiator), timeline scrubber (P1), speed controls (P2), trade price overlay (P2)

**Uses (from STACK.md):** Recharts 3.7 (shadcn chart component, AreaChart with `type="stepAfter"`), requestAnimationFrame + useRef (built-in), Radix Slider (already installed via radix-ui 1.4.3), date-fns for timestamp display

**Implements (from ARCHITECTURE.md):** `replay.py` service (incremental reconstruction algorithm: one snapshot + one delta range scan + sequential walk), `POST /replay` route with `max_time_range` and `frame_count` bounds, `ReplayVisualization`, `OrderbookChart` (Canvas imperative rendering), `useReplay` hook (frame-counting playback, not wall-clock), `ReplayControls`

**Avoids (from PITFALLS.md):** Pitfall 1 (unbounded data — max_time_range enforcement, server-side downsampling, response under 5MB), Pitfall 3 (Canvas not SVG, useRef not useState for animation loop), Pitfall 7 (tab visibility — document.visibilitychange listener, frame-counting not wall-clock elapsed time)

**Research flag:** Needs a targeted design spike during planning. Two specific areas: (1) verify that Recharts AreaChart with `type="stepAfter"` handles the 0-100 cent bounded X-axis correctly for prediction markets (Yes + No as opposing areas meeting at implied probability); (2) validate Canvas rendering approach for OrderbookChart with 99 price levels at 30fps on current hardware. The static depth chart prototype should be built and validated before the full replay engine is constructed.

---

### Phase 4: Coverage Analytics + Pricing Visibility

**Rationale:** Polish and analytics. The calendar heatmap requires the new `GET /coverage/{ticker}/daily` per-day density endpoint (new SQL aggregation against the materialized view). Usage analytics piggybacks on the existing `key_usage_log` table with only an aggregation query. These features add value but are not blockers for anything else and can be deferred if Phase 3 runs long.

**Delivers:** Calendar heatmap of data coverage per market (per-day snapshot/delta density displayed as colored grid), credit cost estimator for replay sessions, usage breakdown by endpoint in billing dashboard.

**Addresses (from FEATURES.md):** Calendar heatmap (P2, differentiator), credit cost estimator (P3), usage breakdown by endpoint (P2)

**Implements (from ARCHITECTURE.md):** `GET /coverage/{ticker}/daily` endpoint, heatmap grid component (custom Tailwind CSS grid, ~30-40 lines, no library needed), `UsageChart` (Recharts BarChart, already installed from Phase 3), billing page enhancement

**Avoids (from PITFALLS.md):** Pitfall 8 (completeness metric — heatmap shows gaps visually rather than a misleading single percentage), security note (coverage detail requires authentication, not public)

**Research flag:** Standard patterns. Postgres date-trunc aggregation, Tailwind grid, Recharts bar chart are all documented. No additional research phase needed.

---

### Phase Ordering Rationale

The ordering follows the feature dependency graph exactly as documented in FEATURES.md:

- **Coverage infrastructure must be first** because every other phase consumes it (playground examples, replay market selection, heatmap data). Building UI before the data model is ready forces rewrites.
- **Playground before replay** because the current playground burns credits on demos. Adding replay (50x more expensive per demo click) before fixing the credit-burning problem creates a conversion-killing user experience at precisely the moment users encounter the signature feature.
- **Static depth chart before animated replay** because the replay engine animates the depth chart component. Verifying the visualization is correct on a static frame before adding animation complexity reduces debugging surface area significantly.
- **Phase 4 is truly independent** — heatmap and analytics add value but block nothing. They can be re-ordered or deferred without impacting v1.2 launch if earlier phases run long.

---

### Research Flags

**Needs research during planning:**
- **Phase 3 (Replay):** Canvas rendering architecture — specifically the interaction between `useRef`-managed canvas, `requestAnimationFrame` loop lifecycle, and React's concurrent mode. Prototype the static depth chart component before building the full replay engine. Also validate Recharts `type="stepAfter"` behavior with prediction market price axes (0-100 bounded, Yes and No opposing areas).

**Standard patterns — skip research-phase:**
- **Phase 1 (Coverage):** Postgres materialized views, TanStack Table, FastAPI route modules, Supabase migrations — all extensively documented.
- **Phase 2 (Playground):** shadcn Command/Combobox autocomplete, JWT auth in FastAPI, static response serving — all standard.
- **Phase 4 (Analytics):** Date aggregation SQL, Tailwind grid heatmap, Recharts bar chart — all standard.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack verified from codebase. New additions (Recharts 3.7, date-fns 4.x) verified via npm and shadcn docs. React 19 compatibility documented with specific workaround (react-is override). |
| Features | HIGH | Codebase reviewed directly for existing endpoint shapes. Competitor analysis (PredictionData.dev, Kalshi native UI, Polymarket) confirms differentiator claims. Feature dependency tree verified against existing API contracts. |
| Architecture | HIGH | All new components designed from direct codebase analysis of existing patterns (reconstruction.py, deps.py, lib/api.ts, playground components). Incremental reconstruction algorithm is a well-known pattern. Materialized view approach is standard Postgres. |
| Pitfalls | HIGH | All pitfalls grounded in existing codebase code paths (actual partition query patterns in markets.py, actual credit deduction flow in deps.py, actual archival code in archival.py). PostgreSQL partition behavior confirmed by multiple primary sources including quantified benchmarks. |

**Overall confidence: HIGH**

### Gaps to Address

- **Recharts `stepAfter` for prediction market depth charts:** The FEATURES.md notes that prediction market depth charts have bounded 0-100 cent axes (Yes and No sides, not Bid and Ask). Research confirms Recharts can render this, but the specific layout (Yes green left-to-right, No red right-to-left, meeting at implied probability) should be prototyped early in Phase 3 before the full replay engine is built. If the depth chart layout requires Canvas anyway, make that decision early rather than late.

- **Replay response size limit:** ARCHITECTURE.md recommends batch response (one JSON object with all frames) for Phase 3 v1. PITFALLS.md recommends streaming (SSE/chunked) to avoid browser OOM. Both agree on server-side downsampling. Recommended resolution: batch with enforced `max_time_range` (4 hours) and `frame_count` cap (120 max frames) for Phase 3, streaming as a Phase 4+ enhancement if users request longer replays. Verify batch payload stays under 5MB before shipping.

- **Coverage completeness definition:** PITFALLS.md explicitly warns against showing a naive percentage. The recommendation is a timeline heatmap (Phase 4) plus sequence gap count (Phase 1). The product decision on whether to show any numeric completeness score at all should be made during Phase 1 planning, not during implementation.

- **date-fns version:** STACK.md notes date-fns 4.x was MEDIUM confidence (not verified via Context7). Low risk — API is stable — but `npm install date-fns` should confirm the version resolves to 4.x during Phase 1 frontend setup.

---

## Sources

### Primary (HIGH confidence — direct codebase or official documentation)
- KalshiBook codebase: `src/api/routes/`, `src/api/services/reconstruction.py`, `src/api/deps.py`, `src/collector/archival.py`, `dashboard/src/components/playground/`, `dashboard/src/lib/api.ts`, `dashboard/package.json`
- [shadcn/ui Chart docs](https://ui.shadcn.com/docs/components/radix/chart) — Recharts integration, ChartContainer
- [shadcn/ui React 19 compatibility guide](https://ui.shadcn.com/docs/react-19) — react-is override for Recharts
- [Recharts npm](https://www.npmjs.com/package/recharts) — v3.7.0 verified
- [Radix UI Slider](https://www.radix-ui.com/primitives/docs/components/slider) — unified radix-ui 1.4.3 compatibility
- [PostgreSQL Materialized Views](https://www.postgresql.org/docs/current/sql-creatematerializedview.html)
- [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- [Next.js Streaming](https://nextjs.org/docs/14/app/building-your-application/routing/loading-ui-and-streaming)

### Secondary (MEDIUM confidence — community consensus, multiple sources agree)
- [PostgresAI: Planning time vs partition count](https://postgres.ai/blog/20241003-how-does-planning-time-depend-on-number-of-partitions) — quantified planning time growth (12ms at 1000 partitions)
- [CYBERTEC: Cross-partition aggregate pitfalls](https://www.cybertec-postgresql.com/en/killing-performance-with-postgresql-partitioning/)
- [pganalyze: Partition-wise aggregates](https://pganalyze.com/blog/5mins-postgres-partition-wise-joins-aggregates-query-performance)
- [QuestDB Market Replay Glossary](https://questdb.com/glossary/market-replay-systems/) — replay architecture patterns
- [Highcharts Depth Chart Guide](https://www.highcharts.com/blog/tutorials/depth-chart-a-visual-guide-to-market-liquidity-and-order-flow/) — depth chart anatomy
- [Nordic APIs: API Sandbox Best Practices](https://nordicapis.com/7-best-practices-for-api-sandboxes/) — free sandbox pattern
- [Plaid Sandbox](https://plaid.com/docs/sandbox/) — industry reference for zero-cost demo environments
- [CoinAPI Order Book Replay Guide](https://www.coinapi.io/blog/crypto-order-book-replay) — snapshot + diff replay patterns
- [SteelEye Order Book Replay](https://www.steel-eye.com/product-features/order-book-replay) — enterprise feature set reference

### Tertiary (LOW confidence — needs validation during implementation)
- Recharts animation smoothness for depth chart at 30fps with step interpolation — may need Canvas fallback if SVG performance is insufficient at higher update rates
- date-fns 4.x version resolution — verify during `npm install`

---
*Research completed: 2026-02-18*
*Ready for roadmap: yes*
