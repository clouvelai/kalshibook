# Stack Research: Discovery & Replay Features

**Domain:** Orderbook replay visualization, market coverage dashboards, playground data population
**Researched:** 2026-02-18
**Confidence:** HIGH (existing stack verified from codebase, new libraries verified via npm/official docs)

**Scope:** This document covers ONLY the new libraries needed for the Discovery & Replay milestone. The existing backend stack (FastAPI/asyncpg/Supabase) and frontend stack (Next.js 15.5/React 19.1/Tailwind 4/shadcn) are already validated and deployed.

---

## Decision Framework

This milestone adds four new concerns to the dashboard:

1. **Orderbook Replay Visualization** -- Animated depth chart + price line showing how a market's orderbook evolved over time, with playback controls (play/pause/scrub).
2. **Market Coverage Dashboard** -- Visual display of which markets have data, what date ranges are covered, and data completeness (snapshot/delta/trade density).
3. **Playground Data Population** -- Replacing hardcoded example values with real captured market data so "Try an example" loads actual tickers and timestamps.
4. **Pricing Validation Tooling** -- Dashboard views to verify credit costs make sense (request counts, response sizes, timing).

---

## Existing Stack (DO NOT ADD -- Already Installed)

These are already in `dashboard/package.json` and working with React 19.1.0 + Next.js 15.5.12:

| Technology | Version | Role |
|------------|---------|------|
| React | 19.1.0 | UI runtime |
| Next.js | 15.5.12 | Framework (App Router) |
| radix-ui | 1.4.3 | Unified Radix primitives (dialog, select, dropdown, switch, tabs, tooltip, etc.) |
| @tanstack/react-table | 8.21.3 | Data tables (keys table) |
| prism-react-renderer | 2.4.1 | Syntax highlighting (playground code block) |
| lucide-react | 0.564.0 | Icons |
| sonner | 2.0.7 | Toast notifications |
| tailwindcss | 4 | Styling |
| shadcn | 3.8.4 | Component generator (devDependency) |
| class-variance-authority | 0.7.1 | Variant utility |
| clsx / tailwind-merge | -- | Class merging |
| @supabase/ssr + supabase-js | -- | Auth |

---

## Recommended Stack Additions

### Charting: Recharts 3.x via shadcn/ui Chart Component

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| recharts | ^3.7.0 | Area charts (depth chart), line charts (price history), bar charts (coverage density) | shadcn/ui's built-in chart system is built on Recharts. The project already uses shadcn for every UI component. Adding `shadcn add chart` gives you pre-styled, theme-consistent ChartContainer, ChartTooltip, ChartLegend components that compose with raw Recharts primitives. No new abstraction to learn -- it IS Recharts, just with shadcn styling wrappers. Recharts 3.7.0 works with React 19.1 via `react-is` override (documented by shadcn). SVG-based rendering is fine for orderbook depth charts where you have 1-99 price levels max (not thousands of data points). |

**Why Recharts over alternatives:**

| Criterion | Recharts (via shadcn) | lightweight-charts | visx |
|-----------|----------------------|-------------------|------|
| Integration with existing stack | Native -- shadcn already built on it | Foreign -- Canvas API, imperative ref-based init | Low-level -- requires building everything from primitives |
| Theme consistency | Automatic -- uses CSS variables from shadcn theme | Manual -- own color system | Manual |
| React 19 compatibility | Works with react-is override (documented) | Works (vanilla JS, React-agnostic via refs) | Works (low-level primitives) |
| Depth chart capability | AreaChart with step interpolation = depth chart | No built-in depth chart; need custom series plugin | AreaClosed + custom work |
| Price line chart | LineChart out of the box | Line series out of the box (this is its strength) | LinePath + custom work |
| Bundle size | ~200KB (SVG-based) | ~35KB (Canvas-based) | ~varies by packages imported |
| Learning curve for team | Zero -- same JSX patterns as rest of dashboard | Medium -- imperative API, Canvas concepts | High -- D3-like mental model |
| Ideal for | Dashboards, admin panels, <1000 data points | Financial trading UIs, real-time streaming | Bespoke data viz, custom interactions |

**The orderbook depth chart is NOT a trading terminal.** It is a visualization in a SaaS dashboard showing historical data replay. Recharts' SVG approach is perfectly suited: max 99 price levels per side, no streaming, no real-time requirements. lightweight-charts would be over-engineered (and under-styled for this dashboard).

### Playback Animation: No Library Needed

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| requestAnimationFrame + useRef | Built-in | Playback timeline animation loop | The replay feature needs: play/pause, speed control (0.5x/1x/2x/5x), timeline scrubbing. This is a simple `requestAnimationFrame` loop advancing through a pre-fetched array of orderbook states. No animation library needed. A single `useReplayPlayback` custom hook (~50 lines) handles: current frame index, play/pause state, speed multiplier, scrub-to-position. React 19's concurrent features and `useRef` for mutable frame state avoid re-render overhead during playback. |

**Why NOT use Framer Motion / react-spring / GSAP:**
- Those libraries animate CSS properties (opacity, transform, position). We need to advance a data index through time and re-render a chart. Fundamentally different use case.
- Adding a 50KB+ animation library to increment a counter is absurd.
- `requestAnimationFrame` + `useRef` is the correct primitive for data-driven playback.

### Slider/Scrubber: shadcn Slider (Already Available)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Radix Slider (via radix-ui) | 1.4.3 (already installed) | Timeline scrubber for replay playback | The project already has `radix-ui` 1.4.3 installed. `shadcn add slider` generates a Slider component wrapping `Slider` from `radix-ui`. This gives: keyboard accessible, touch-friendly, ARIA-labeled range input. Perfect for scrubbing through the replay timeline. No new dependency needed. |

**Important note on React 19:** There was a reported crash with `@radix-ui/react-slider` 1.3.6 on React 19 (GitHub issue #3721). However, the project uses the unified `radix-ui` 1.4.3 package which includes the latest versions of all primitives with React 19 compatibility fixes. If the slider crashes at runtime, the workaround is to use a native HTML `<input type="range">` styled with Tailwind -- this is trivial for a single scrubber control.

### Date/Time Handling: date-fns

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| date-fns | ^4.1.0 | Format timestamps, parse ISO dates, calculate date ranges for coverage | Tree-shakable (import only what you use), functional API, immutable. The dashboard needs to: format ISO timestamps for display, calculate day boundaries for coverage heatmaps, compute relative time ("3 hours ago"). date-fns does all of this at ~2-5KB for the functions actually imported. No global locale setup needed (unlike dayjs). Works with native Date objects -- no wrapper class to learn. |

**Why NOT dayjs:** dayjs is 2KB total but uses a Moment-like mutable wrapper API (`dayjs(date).format()`). date-fns works with plain `Date` objects and functional composition (`format(date, pattern)`), which matches React's functional component style better. Tree-shaking makes bundle size comparison moot.

**Why NOT luxon/moment:** Dead weight. Luxon is 30KB. Moment is deprecated.

### Market Coverage Heatmap: Custom Component (Not a Library)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Custom SVG grid | N/A | Calendar heatmap showing data coverage per market per day | A coverage heatmap for date ranges is a simple grid: days on X axis, markets on Y axis, color = data density. This is a 30-40 line React component rendering `<div>` cells with Tailwind background colors. No library needed. Libraries like `@uiw/react-heat-map` or `react-calendar-heatmap` add dependencies for a component that is trivial to build with the existing Tailwind + shadcn design system. If coverage needs GitHub-style contribution graphs later, `recharts` (already added) can render a custom heatmap via its existing primitives. |

### Data Tables: @tanstack/react-table (Already Installed)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| @tanstack/react-table | 8.21.3 (already installed) | Market list with sorting, filtering, search | Already used for the API keys table. Market coverage table is the same pattern: tabular data, sortable columns, optional filtering. Zero new dependencies. |

---

## Backend: No New Dependencies

The existing Python backend (FastAPI + asyncpg + Supabase Postgres) already has everything needed:

| Capability | Existing Support | What Changes |
|------------|-----------------|--------------|
| Market listing with coverage dates | `GET /markets` already returns `first_data_at`, `last_data_at` | Add `snapshot_count`, `delta_count` to list endpoint (already on detail) |
| Orderbook reconstruction at any timestamp | `POST /orderbook` with snapshot+delta replay | No change -- frontend calls this N times for replay frames |
| Delta stream for replay | `POST /deltas` with cursor pagination | No change -- frontend fetches deltas for a time range |
| Trade history | `POST /trades` with cursor pagination | No change |
| Candle data | `GET /candles/{ticker}` | No change |
| Coverage density per day | Not exposed | Add new `GET /markets/{ticker}/coverage` endpoint returning per-day snapshot/delta/trade counts. Simple SQL aggregation on existing partitioned tables. |
| Playground example data | Not exposed | Add new internal (non-credit-costing) `GET /playground/examples` endpoint that returns real market tickers + timestamps with confirmed data. |

**No new Python packages needed.** asyncpg + SQL is sufficient for the new queries.

---

## Installation

### Frontend (dashboard/)

```bash
# Add shadcn chart component (brings in recharts as dependency)
cd /Users/samuelclark/Desktop/kalshibook/dashboard
npx shadcn@latest add chart

# Add shadcn slider component (no new dependency -- uses existing radix-ui)
npx shadcn@latest add slider

# Add date-fns for timestamp formatting
npm install date-fns

# React 19 compatibility: add react-is override to package.json
# (shadcn chart docs require this for recharts)
```

After running `shadcn add chart`, add this to `dashboard/package.json`:

```json
{
  "overrides": {
    "react-is": "^19.0.0"
  }
}
```

Then `npm install` to apply the override.

### Backend

```bash
# No new packages needed
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not the Alternative |
|----------|-------------|-------------|------------------------|
| Charting | Recharts 3.x (via shadcn chart) | TradingView lightweight-charts 5.1 | Imperative Canvas API doesn't match React dashboard patterns. Requires manual theme integration. Over-engineered for displaying 99 price levels in a SaaS dashboard. Correct choice for a real-time trading terminal; wrong choice here. |
| Charting | Recharts 3.x (via shadcn chart) | visx (Airbnb) | Low-level D3 primitives require building chart components from scratch (scales, axes, areas, interactions). 10x more code for the same result. Correct choice for highly bespoke visualization; wrong choice for standard charts in an admin dashboard. |
| Charting | Recharts 3.x (via shadcn chart) | Chart.js / react-chartjs-2 | Imperative Canvas API like lightweight-charts. Less financial-domain awareness. shadcn has no Chart.js integration. Would be a foreign element in an otherwise consistent shadcn UI. |
| Charting | Recharts 3.x (via shadcn chart) | Nivo | Heavier than Recharts, less community adoption, no shadcn integration. Good library, but adds complexity without benefit when shadcn already wraps Recharts. |
| Playback | requestAnimationFrame + useRef | Framer Motion | Animates DOM properties, not data indices. 50KB bundle for a feature that needs a counter incrementing at configurable speed. |
| Playback | requestAnimationFrame + useRef | react-spring | Same issue as Framer Motion -- physics-based CSS animations, not data playback. |
| Date utils | date-fns | dayjs | Wrapper-object API (`dayjs()`) vs functional (`format(date)`). Tree-shaking is roughly equivalent. date-fns aligns with functional React patterns. Either would work -- preference, not requirement. |
| Date utils | date-fns | No library (manual) | ISO parsing and formatting are error-prone to hand-roll (timezone edge cases, locale formatting). date-fns is < 5KB imported for what we need. Worth it. |
| Coverage heatmap | Custom Tailwind component | @uiw/react-heat-map | GitHub-contribution-style heatmap library. Adds a dependency for a component that is literally a grid of colored divs. Over-engineering. If the project later needs a complex interactive heatmap, recharts (already installed) can do it. |
| Coverage heatmap | Custom Tailwind component | react-calendar-heatmap | Same reasoning. SVG-based calendar component. Our coverage display is a simple grid, not a full calendar. |
| Slider | shadcn Slider (Radix) | rc-slider | Already have Radix slider via the unified radix-ui package. Adding another slider library creates inconsistency. |
| Data tables | @tanstack/react-table (existing) | AG Grid | Enterprise-grade overkill for a market list. Already using tanstack for keys table -- consistency matters. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| D3.js (direct) | Imperative DOM manipulation conflicts with React's declarative model. Recharts wraps the useful D3 parts already. | Recharts (wraps D3 scales/shapes internally) |
| lightweight-charts for depth chart | Canvas-based financial charting library designed for real-time trading terminals. The orderbook replay is a SaaS dashboard feature, not a terminal. Imperative API requires ref-based initialization foreign to the rest of the codebase. | Recharts AreaChart with step interpolation |
| Any WebSocket library for replay | Replay is historical data playback, not live streaming. Fetching a batch of states and playing through them client-side is simpler, cheaper, and works offline. | Batch fetch via REST, client-side playback loop |
| react-player / video.js | Replay is NOT a video. It is data-driven chart re-rendering at configurable speed. | Custom useReplayPlayback hook with requestAnimationFrame |
| zustand / jotai / redux for replay state | The replay state is local to one page component (current frame, play/pause, speed). React useState + useRef is sufficient. Adding a state management library for one component is unnecessary. | useState + useRef in useReplayPlayback hook |
| moment.js | Deprecated. 300KB. Mutable API. | date-fns |
| axios | The dashboard already uses native `fetch` (via lib/api.ts). Adding axios introduces a second HTTP pattern. | Native fetch (existing pattern) |

---

## Complete New Dependency Summary

| Package | Category | Bundle Impact | Why |
|---------|----------|---------------|-----|
| recharts | Charting | ~200KB | Depth chart + price line + coverage bar chart. Installed via `shadcn add chart`. |
| date-fns | Date utility | ~2-5KB (tree-shaken) | Timestamp formatting, date range calculation. |

**Total new dependencies: 2.** Everything else uses existing installed packages (radix-ui, @tanstack/react-table, lucide-react) or built-in browser APIs (requestAnimationFrame, Canvas).

---

## Version Compatibility Matrix

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| recharts ^3.7.0 | React 19.1.0 | Requires `react-is` override in package.json. Documented by shadcn. |
| recharts ^3.7.0 | Next.js 15.5 | Server components: chart components must be `"use client"`. |
| date-fns ^4.1.0 | Any (pure JS) | No React dependency. Works everywhere. |
| radix-ui 1.4.3 (Slider) | React 19.1.0 | Unified package resolves earlier React 19 issues. Already installed and tested. |
| @tanstack/react-table 8.21.3 | React 19.1.0 | Already working in production (keys table). |
| shadcn 3.8.4 | radix-ui 1.4.3 | Already installed and configured. `shadcn add chart` and `shadcn add slider` use existing setup. |

---

## Stack Patterns by Feature

**Orderbook Depth Chart (replay frame):**
- Recharts `<AreaChart>` with two mirrored `<Area>` components (yes side green, no side red)
- `type="step"` interpolation to show discrete price levels (orderbooks are stepwise, not smooth)
- X-axis = price (1-99 cents), Y-axis = cumulative quantity
- Data comes from a single `POST /orderbook` response (yes[] + no[] arrays)
- Wrapped in shadcn `<ChartContainer>` for consistent sizing

**Price Line Chart (replay overlay):**
- Recharts `<LineChart>` or `<ComposedChart>` combining price line with trade markers
- Data from `POST /trades` responses during the replay time window
- Synchronized X-axis (time) with the replay timeline

**Replay Playback:**
- `useReplayPlayback(frames, { speed, onFrame })` custom hook
- Pre-fetches N orderbook states across the time range via `POST /orderbook` calls
- `requestAnimationFrame` loop advances frame index at `speed` rate
- Radix Slider for timeline scrubbing
- Play/Pause button (lucide-react icons already available)

**Market Coverage Table:**
- `@tanstack/react-table` (existing) with columns: ticker, title, status, first_data, last_data, snapshot_count, delta_count
- Sortable, filterable
- Custom Tailwind heatmap cells for date range visualization

**Playground Data Population:**
- New `GET /playground/examples` backend endpoint (no credits, auth-only)
- Returns array of `{ ticker, timestamp, description }` objects with confirmed data
- `usePlayground` hook calls this on mount, populates "Try an example" dropdown

---

## Sources

- [shadcn/ui Chart docs](https://ui.shadcn.com/docs/components/radix/chart) -- Recharts-based, composition approach, install via `shadcn add chart` (HIGH)
- [shadcn/ui React 19 compatibility guide](https://ui.shadcn.com/docs/react-19) -- react-is override documented for Recharts (HIGH)
- [shadcn/ui Recharts v3 PR #8486](https://github.com/shadcn-ui/ui/pull/8486) -- Recharts v3 support merged (HIGH)
- [shadcn/ui Recharts v3 issue #7669](https://github.com/shadcn-ui/ui/issues/7669) -- Community fix for v3 type changes (HIGH)
- [Recharts npm](https://www.npmjs.com/package/recharts) -- v3.7.0, published Jan 2026 (HIGH)
- [Recharts GitHub releases](https://github.com/recharts/recharts/releases) -- v3.x active development (HIGH)
- [shadcn/ui Area Charts gallery](https://ui.shadcn.com/charts/area) -- Pre-built area chart variants (HIGH)
- [TradingView lightweight-charts](https://tradingview.github.io/lightweight-charts/) -- v5.1.0, Canvas-based, 35KB (HIGH -- evaluated and rejected for this use case)
- [lightweight-charts React tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) -- Ref-based integration pattern (HIGH)
- [lightweight-charts series types](https://tradingview.github.io/lightweight-charts/docs/series-types) -- Area, Line, Candlestick, Custom (HIGH)
- [visx gallery](https://airbnb.io/visx/gallery) -- Low-level primitives, AreaClosed component (HIGH)
- [Radix UI Slider](https://www.radix-ui.com/primitives/docs/components/slider) -- Part of radix-ui unified package (HIGH)
- [Radix Slider React 19 issue #3721](https://github.com/radix-ui/primitives/issues/3721) -- Crash fixed in unified package (HIGH)
- [shadcn February 2026 unified radix-ui migration](https://ui.shadcn.com/docs/changelog/2026-02-radix-ui) -- Confirmed radix-ui 1.4.3 compatibility (HIGH)
- [date-fns npm](https://www.npmjs.com/package/date-fns) -- v4.x, tree-shakable, functional API (MEDIUM -- version not verified via Context7)
- [date-fns vs dayjs comparison](https://www.dhiwise.com/post/date-fns-vs-dayjs-the-battle-of-javascript-date-libraries) -- Functional vs wrapper API tradeoff (MEDIUM)
- [React orderbook visualization patterns](https://www.freecodecamp.org/news/react-websockets-project-build-real-time-order-book-app/) -- CSS-based depth bars, Canvas layering approaches (MEDIUM)
- [requestAnimationFrame MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame) -- Browser API for playback loops (HIGH)
- [Using requestAnimationFrame with React hooks](https://css-tricks.com/using-requestanimationframe-with-react-hooks/) -- useRef pattern for mutable frame state (MEDIUM)
- [@uiw/react-heat-map npm](https://www.npmjs.com/package/@uiw/react-heat-map) -- Evaluated and rejected; custom Tailwind grid simpler (MEDIUM)
- [KalshiBook codebase](file:///Users/samuelclark/Desktop/kalshibook) -- dashboard/package.json, src/api/routes/*, src/api/models.py reviewed directly (HIGH)

---
*Stack research for: KalshiBook Discovery & Replay Features*
*Researched: 2026-02-18*
