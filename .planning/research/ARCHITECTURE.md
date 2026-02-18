# Architecture Research: Discovery & Replay Feature Integration

**Domain:** Orderbook replay visualization, market coverage dashboards, and playground data population for existing financial data API platform
**Researched:** 2026-02-18
**Confidence:** HIGH (based on direct codebase analysis of all existing components + proven patterns for similar features)

## Existing System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          NEXT.JS DASHBOARD (port 3000)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Overview  │  │Playground│  │ API Keys │  │ Billing  │  │  [NEW PAGES] │ │
│  │  page.tsx │  │ page.tsx │  │ page.tsx │  │ page.tsx │  │  coverage/   │ │
│  │           │  │          │  │          │  │          │  │  replay/     │ │
│  └─────┬────┘  └─────┬────┘  └──────────┘  └──────────┘  └──────┬───────┘ │
│        │              │                                          │         │
│  ┌─────┴──────────────┴──────────────────────────────────────────┴───────┐ │
│  │                         lib/api.ts (fetchAPI)                         │ │
│  │              /api/* rewrite -> http://localhost:8000/*                 │ │
│  └───────────────────────────────────┬───────────────────────────────────┘ │
└──────────────────────────────────────┼─────────────────────────────────────┘
                                       │ HTTP
┌──────────────────────────────────────┼─────────────────────────────────────┐
│                      FASTAPI (port 8000)                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Routes: /orderbook  /deltas  /markets  /trades  /settlements       │  │
│  │          /candles  /events  /auth  /keys  /billing                  │  │
│  │          [NEW: /coverage  /replay  /playground/*]                    │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │  Services: reconstruction.py  candles.py  billing.py  auth.py       │  │
│  │            [NEW: coverage.py  replay.py]                            │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │  Deps: get_db_pool  require_credits  get_api_key  get_auth_user    │  │
│  └──────────────────────────┬───────────────────────────────────────────┘  │
│                              │ asyncpg pool                                │
└──────────────────────────────┼─────────────────────────────────────────────┘
                               │
┌──────────────────────────────┼─────────────────────────────────────────────┐
│                    SUPABASE POSTGRES (daily-partitioned)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │snapshots │  │ deltas   │  │ trades   │  │ markets  │  │ events/     │ │
│  │(daily)   │  │(daily)   │  │(daily)   │  │          │  │ series/     │ │
│  │          │  │          │  │          │  │          │  │ settlements │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │
│  [NEW: materialized view: market_coverage_stats]                          │
└───────────────────────────────────────────────────────────────────────────┘
                               ^
                               │ writes
┌──────────────────────────────┼─────────────────────────────────────────────┐
│                     COLLECTOR SERVICE                                       │
│  WS -> Processor -> Writer -> Supabase                                     │
│  Discovery -> lifecycle -> subscribe/unsubscribe                           │
│  Enrichment -> REST API -> events/series/settlements                       │
└────────────────────────────────────────────────────────────────────────────┘
```

## Integration Architecture for New Features

### Feature 1: Market Coverage Visibility

**What it does:** Shows users which markets have data, date ranges, data density, and status. Currently, `/markets` returns `first_data_at` and `last_data_at` per market, but runs expensive subqueries (MIN/MAX on snapshots + deltas tables) on every call.

**Architecture approach:** Pre-compute coverage statistics rather than querying raw tables per request.

#### New Backend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `market_coverage_stats` | Materialized view | Supabase migration | Pre-computed coverage: market_ticker, first_data_at, last_data_at, snapshot_count, delta_count, trade_count, last_refreshed |
| `coverage.py` (service) | Service module | `src/api/services/coverage.py` | Query materialized view, aggregate by category/event |
| `coverage.py` (route) | Route module | `src/api/routes/coverage.py` | `GET /coverage` (summary), `GET /coverage/{ticker}` (detail) |
| Coverage response models | Models | `src/api/models.py` | `CoverageSummary`, `CoverageDetail`, `CoverageResponse` |
| Refresh function | SQL function | Supabase migration | `REFRESH MATERIALIZED VIEW CONCURRENTLY market_coverage_stats` |

#### New Frontend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| Coverage page | Page | `dashboard/src/app/(dashboard)/coverage/page.tsx` | Market coverage dashboard |
| `CoverageTable` | Component | `dashboard/src/components/coverage/coverage-table.tsx` | Sortable table of markets with data ranges |
| `CoverageFilters` | Component | `dashboard/src/components/coverage/coverage-filters.tsx` | Filter by category, status, date range |
| `CoverageSummaryCards` | Component | `dashboard/src/components/coverage/summary-cards.tsx` | Aggregate stats cards (total markets, total snapshots, etc.) |
| `useCoverage` | Hook | `dashboard/src/components/coverage/use-coverage.ts` | Fetch and manage coverage data state |
| Coverage API methods | API client | `dashboard/src/lib/api.ts` | `api.coverage.list()`, `api.coverage.detail(ticker)` |

#### Data Flow

```
Dashboard coverage page
    |
    v
useCoverage hook -> api.coverage.list() -> /api/coverage
    |                                          |
    v                                          v
CoverageTable <-------- JSON response ---- FastAPI /coverage
CoverageSummaryCards                            |
CoverageFilters                                 v
                                      coverage.py service
                                            |
                                            v
                                   market_coverage_stats (materialized view)
                                   refreshed periodically by pg_cron or API call
```

#### Modifications to Existing Components

| Existing Component | Change | Rationale |
|-------------------|--------|-----------|
| `app-sidebar.tsx` | Add "Coverage" nav item with `BarChart3` icon | New page needs sidebar entry |
| `src/api/main.py` | Register `coverage.router` | New route module |
| `src/api/models.py` | Add coverage-related Pydantic models | Response types for new endpoints |
| `dashboard/src/lib/api.ts` | Add `api.coverage` namespace | Frontend API client methods |
| `dashboard/src/types/api.ts` | Add `CoverageSummary` and `CoverageDetail` interfaces | TypeScript types |

#### Why Materialized View

The existing `/markets` endpoint runs `SELECT MIN(captured_at) FROM snapshots WHERE market_ticker = $1` and `SELECT MAX(ts) FROM deltas WHERE market_ticker = $1` for **every market** in a loop (the list endpoint) or as subqueries. With daily-partitioned tables growing over time, these become progressively slower. A materialized view pre-computes once and serves instantly. `REFRESH MATERIALIZED VIEW CONCURRENTLY` allows zero-downtime refreshes.

---

### Feature 2: Orderbook Replay Visualization

**What it does:** Animates orderbook state changes over a time window, showing the book evolving as deltas arrive. Users specify a market, start time, end time, and playback speed.

**Architecture approach:** Fetch a batch of reconstruction frames server-side, stream them to the client, animate with `requestAnimationFrame`.

#### Option A: Batch Endpoint (Recommended)

A single endpoint that returns N orderbook states at evenly-spaced intervals. This is simpler, works with the existing credit system, and avoids SSE complexity.

#### Option B: SSE Streaming (Not recommended for v1)

SSE streaming would require holding a connection open, complicates the credit billing model (charge per connection vs per frame?), and adds infrastructure complexity. Defer to a later milestone if users request real-time streaming.

#### New Backend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `replay.py` (service) | Service module | `src/api/services/replay.py` | Batch-reconstruct orderbook at N timestamps across a time range |
| `replay.py` (route) | Route module | `src/api/routes/replay.py` | `POST /replay` endpoint |
| Replay request/response models | Models | `src/api/models.py` | `ReplayRequest`, `ReplayFrame`, `ReplayResponse` |

#### New Frontend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| Replay page | Page | `dashboard/src/app/(dashboard)/replay/page.tsx` | Orderbook replay viewer |
| `ReplayForm` | Component | `dashboard/src/components/replay/replay-form.tsx` | Market picker, time range, speed controls |
| `ReplayVisualization` | Component | `dashboard/src/components/replay/replay-visualization.tsx` | Animated orderbook + depth chart |
| `ReplayControls` | Component | `dashboard/src/components/replay/replay-controls.tsx` | Play/pause, scrubber, speed selector |
| `OrderbookChart` | Component | `dashboard/src/components/replay/orderbook-chart.tsx` | Depth-style visualization of yes/no levels |
| `useReplay` | Hook | `dashboard/src/components/replay/use-replay.ts` | Manages replay state, frame progression, animation loop |
| Replay API methods | API client | `dashboard/src/lib/api.ts` | `api.replay.fetch(params)` |

#### Replay Service Algorithm

```python
# src/api/services/replay.py

async def generate_replay_frames(
    pool: asyncpg.Pool,
    market_ticker: str,
    start_time: datetime,
    end_time: datetime,
    frame_count: int = 60,  # default: 60 frames
    depth: int | None = 10,
) -> list[dict]:
    """Generate a series of orderbook states across a time range.

    Algorithm:
    1. Compute evenly-spaced timestamps between start and end
    2. For each timestamp, call reconstruct_orderbook()
    3. Return array of {timestamp, yes, no} frames

    Optimization: Instead of N independent reconstructions from scratch,
    reconstruct once at start_time, then incrementally apply deltas
    to advance to each subsequent timestamp. This avoids re-scanning
    the entire delta range for each frame.
    """
    # Step 1: Find the base snapshot before start_time
    # Step 2: Fetch ALL deltas between start_time and end_time in one query
    # Step 3: Walk through deltas, emitting a frame at each target timestamp
    pass
```

The key optimization is **incremental reconstruction**: fetch all deltas for the full time range once, then walk through them emitting frames at evenly-spaced intervals. This is O(D) where D = total deltas, rather than O(N * D) for N independent reconstructions.

#### Data Flow

```
Replay page
    |
    v
ReplayForm -> user sets market, time range, speed
    |
    v (on submit)
useReplay hook -> api.replay.fetch({market, start, end, frames: 60}) -> POST /api/replay
    |                                                                         |
    |                                                                         v
    |                                                              replay.py service
    |                                                                   |
    |                                                     incremental reconstruction
    |                                                     (1 snapshot + N delta walks)
    |                                                                   |
    v                                                                   v
frames[] <---------- JSON {frames: [{ts, yes, no}, ...]} ----------- response
    |
    v
useReplay: requestAnimationFrame loop
    |  - current frame index advances based on playback speed
    |  - interpolation optional for smooth transitions
    v
ReplayVisualization (renders current frame)
    ├── OrderbookChart (depth bars for yes/no)
    └── ReplayControls (play/pause/scrub/speed)
```

#### Animation Architecture

The `useReplay` hook manages the animation loop:

```typescript
// Pseudocode for useReplay animation core
function useReplay() {
  const [frames, setFrames] = useState<ReplayFrame[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1); // 1x, 2x, 4x, 0.5x
  const lastTimeRef = useRef(0);
  const frameIntervalMs = useRef(0); // ms between frames at 1x speed

  useEffect(() => {
    if (!isPlaying || frames.length === 0) return;

    let animId: number;
    const tick = (now: number) => {
      const elapsed = now - lastTimeRef.current;
      const targetInterval = frameIntervalMs.current / speed;

      if (elapsed >= targetInterval) {
        setCurrentIndex(prev => {
          if (prev >= frames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
        lastTimeRef.current = now;
      }
      animId = requestAnimationFrame(tick);
    };

    lastTimeRef.current = performance.now();
    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, speed, frames.length]);

  return { frames, currentIndex, isPlaying, speed, /* actions */ };
}
```

**No animation library needed.** The orderbook is a table of numbers that change between frames. Using `requestAnimationFrame` directly is simpler and more performant than pulling in framer-motion or react-spring for what is essentially "swap the data backing a table every N milliseconds." Animation libraries add value for enter/exit transitions and layout changes, but the replay is fundamentally a data-driven ticker, not a layout animation.

#### Replay Visualization Rendering

The `OrderbookChart` renders depth bars (horizontal bars sized by quantity at each price level), not a traditional chart library. This is CSS-driven:

```
YES SIDE                          NO SIDE
97c |========     50 |            97c |===        30 |
95c |=============80 |            95c |======     60 |
93c |=====        40 |            93c |==========100|
```

Each price level is a flex row with a colored bar sized proportionally to quantity. As frames advance, the bar widths change. No chart library is needed -- this is HTML/CSS with dynamic widths.

---

### Feature 3: Playground Data Population

**What it does:** Pre-loads the playground form with real market tickers and valid timestamps so users do not have to guess valid inputs. Currently, `fillExample()` hardcodes `KXBTC-25FEB14-T96074.99` with a fixed timestamp.

**Architecture approach:** Add a lightweight endpoint that returns a few "example-ready" markets with their data coverage, then update the playground to use it for the "Try an example" feature and add a market search/autocomplete.

#### New Backend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `GET /playground/examples` | Route | `src/api/routes/playground.py` | Returns 3-5 markets with active data + valid timestamp ranges, no credit cost |
| `GET /playground/search?q=` | Route | `src/api/routes/playground.py` | Market ticker autocomplete, no credit cost |

These endpoints are **dashboard-internal** (authenticated via Supabase JWT, not API key). They do not consume credits because they serve the dashboard UI, not the external API.

#### New Frontend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `MarketPicker` | Component | `dashboard/src/components/playground/market-picker.tsx` | Typeahead search for market tickers |
| `ExampleCards` | Component | `dashboard/src/components/playground/example-cards.tsx` | Clickable example market cards |

#### Modifications to Existing Components

| Existing Component | Change | Rationale |
|-------------------|--------|-----------|
| `use-playground.ts` | Replace hardcoded `fillExample()` with data from `/playground/examples`. Add `loadExamples()` on mount. Add market search state. | Dynamic example data |
| `playground-form.tsx` | Replace text Input for market_ticker with `MarketPicker` component. Replace "Try an example" link with `ExampleCards`. | Richer UX with real data |
| `src/api/main.py` | Register `playground.router` | New route module |
| `src/api/deps.py` | No changes needed -- `get_authenticated_user` already exists for JWT auth | Reuse existing auth dependency |

#### Data Flow

```
Playground page mounts
    |
    v
usePlayground.loadExamples() -> fetchAPI("/playground/examples") -> GET /api/playground/examples
    |                                                                     |
    v                                                                     v
ExampleCards <---- [{ticker, title, first_data_at, last_data_at}] ---- Query markets table
    |                                                                  (top 5 by delta_count
    |                                                                   WHERE status='active')
    v (user clicks card)
Form auto-fills: market_ticker, timestamp (midpoint of range), depth=10

User types in market_ticker input
    |
    v
MarketPicker.onSearch(q) -> fetchAPI("/playground/search?q=KXBTC") -> GET /api/playground/search
    |                                                                       |
    v                                                                       v
Dropdown results <--- [{ticker, title, status}] ---- ILIKE query on markets.ticker
    |
    v (user selects)
Form auto-fills: market_ticker
usePlayground fetches coverage for selected market to suggest valid timestamps
```

---

### Feature 4: Pricing Validation / Usage Analytics

**What it does:** Provides visibility into credit consumption patterns for pricing decisions.

**Architecture approach:** The existing `key_usage_log` table (populated by `log_key_usage` in `deps.py`) already captures per-request usage. Aggregate it for analytics.

#### New Backend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `GET /billing/analytics` | Route | `src/api/routes/billing.py` (modify existing) | Usage over time, by endpoint, by key |
| Analytics response models | Models | `src/api/models.py` | `UsageAnalytics`, `EndpointUsage` |

#### New Frontend Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `UsageChart` | Component | `dashboard/src/components/billing/usage-chart.tsx` | Credits over time chart |
| Billing page enhancement | Modify existing | `dashboard/src/app/(dashboard)/billing/page.tsx` | Add analytics section below existing content |

This is the smallest feature and can piggyback on the existing billing page -- no new page needed.

---

## Component Boundary Map

### Backend: New vs Modified Files

```
src/api/
├── main.py                          [MODIFY] Register 3 new routers
├── models.py                        [MODIFY] Add ~8 new Pydantic models
├── routes/
│   ├── coverage.py                  [NEW] Market coverage endpoints
│   ├── replay.py                    [NEW] Orderbook replay endpoint
│   ├── playground.py                [NEW] Playground examples + search
│   └── billing.py                   [MODIFY] Add analytics endpoint
├── services/
│   ├── coverage.py                  [NEW] Coverage aggregation logic
│   ├── replay.py                    [NEW] Incremental reconstruction for replay
│   └── reconstruction.py           [EXISTING, no changes] Reused by replay service
└── deps.py                          [EXISTING, no changes]
```

### Frontend: New vs Modified Files

```
dashboard/src/
├── app/(dashboard)/
│   ├── coverage/
│   │   └── page.tsx                 [NEW] Coverage dashboard page
│   ├── replay/
│   │   └── page.tsx                 [NEW] Replay viewer page
│   └── playground/
│       └── page.tsx                 [EXISTING, minor modification]
├── components/
│   ├── coverage/
│   │   ├── coverage-table.tsx       [NEW]
│   │   ├── coverage-filters.tsx     [NEW]
│   │   ├── summary-cards.tsx        [NEW]
│   │   └── use-coverage.ts          [NEW]
│   ├── replay/
│   │   ├── replay-form.tsx          [NEW]
│   │   ├── replay-visualization.tsx [NEW]
│   │   ├── replay-controls.tsx      [NEW]
│   │   ├── orderbook-chart.tsx      [NEW]
│   │   └── use-replay.ts           [NEW]
│   ├── playground/
│   │   ├── market-picker.tsx        [NEW]
│   │   ├── example-cards.tsx        [NEW]
│   │   ├── playground-form.tsx      [MODIFY] Use MarketPicker, ExampleCards
│   │   └── use-playground.ts        [MODIFY] Dynamic examples, search state
│   ├── billing/
│   │   └── usage-chart.tsx          [NEW]
│   └── sidebar/
│       └── app-sidebar.tsx          [MODIFY] Add Coverage + Replay nav items
├── lib/
│   └── api.ts                       [MODIFY] Add coverage, replay, playground namespaces
└── types/
    └── api.ts                       [MODIFY] Add new TypeScript interfaces
```

### Database: New Objects

```
Supabase migrations:
├── create_market_coverage_stats_matview.sql    [NEW] Materialized view
├── create_refresh_coverage_function.sql        [NEW] Refresh function
└── (optional) pg_cron schedule for refresh     [NEW] If using pg_cron
```

---

## Architectural Patterns

### Pattern 1: Incremental Reconstruction (for Replay)

**What:** Instead of reconstructing the orderbook independently at N timestamps (each requiring snapshot lookup + delta scan), reconstruct once at the start and walk forward through deltas, emitting frames at target timestamps.

**When to use:** Any time you need multiple orderbook states across a contiguous time range.

**Trade-offs:**
- Pro: O(D) instead of O(N * D) where D = delta count, N = frame count
- Pro: Single database query for all deltas instead of N queries
- Con: Must process all deltas even if only a few frames are needed (acceptable because frame_count is bounded at 60-120)

**Example:**
```python
async def generate_replay_frames(pool, market_ticker, start_time, end_time, frame_count=60, depth=10):
    # 1. Compute target timestamps
    interval = (end_time - start_time) / frame_count
    targets = [start_time + interval * i for i in range(frame_count + 1)]

    # 2. Get base snapshot before start_time
    snapshot = await get_nearest_snapshot(pool, market_ticker, start_time)
    yes_book = {level[0]: level[1] for level in snapshot["yes_levels"]}
    no_book = {level[0]: level[1] for level in snapshot["no_levels"]}

    # 3. Fetch ALL deltas from snapshot to end_time in one query
    deltas = await get_deltas_range(pool, market_ticker, snapshot["captured_at"], end_time)

    # 4. Walk through deltas, emit frame at each target timestamp
    frames = []
    target_idx = 0
    for delta in deltas:
        # Emit frames for all targets before this delta's timestamp
        while target_idx < len(targets) and delta["ts"] > targets[target_idx]:
            frames.append(snapshot_to_frame(yes_book, no_book, targets[target_idx], depth))
            target_idx += 1
        # Apply delta
        apply_delta(yes_book, no_book, delta)

    # Emit remaining frames after last delta
    while target_idx < len(targets):
        frames.append(snapshot_to_frame(yes_book, no_book, targets[target_idx], depth))
        target_idx += 1

    return frames
```

### Pattern 2: Materialized View for Aggregated Coverage

**What:** Use a Postgres materialized view to pre-compute expensive aggregation queries, refresh on a schedule.

**When to use:** Queries that scan large partitioned tables (snapshots, deltas, trades) for aggregate stats that don't need sub-second freshness.

**Trade-offs:**
- Pro: Coverage endpoint responds in <10ms instead of 1-5 seconds
- Pro: No load on partitioned tables for dashboard traffic
- Con: Data is stale by the refresh interval (5-15 minutes is fine for coverage stats)
- Con: `REFRESH MATERIALIZED VIEW CONCURRENTLY` requires a unique index

**Example:**
```sql
CREATE MATERIALIZED VIEW market_coverage_stats AS
SELECT
    m.ticker,
    m.title,
    m.event_ticker,
    m.status,
    m.category,
    (SELECT MIN(captured_at) FROM snapshots WHERE market_ticker = m.ticker) AS first_snapshot_at,
    (SELECT MAX(captured_at) FROM snapshots WHERE market_ticker = m.ticker) AS last_snapshot_at,
    (SELECT COUNT(*) FROM snapshots WHERE market_ticker = m.ticker) AS snapshot_count,
    (SELECT MIN(ts) FROM deltas WHERE market_ticker = m.ticker) AS first_delta_at,
    (SELECT MAX(ts) FROM deltas WHERE market_ticker = m.ticker) AS last_delta_at,
    (SELECT COUNT(*) FROM deltas WHERE market_ticker = m.ticker) AS delta_count,
    (SELECT COUNT(*) FROM trades WHERE market_ticker = m.ticker) AS trade_count,
    NOW() AS refreshed_at
FROM markets m;

CREATE UNIQUE INDEX ON market_coverage_stats (ticker);
```

### Pattern 3: Dashboard-Internal Endpoints (No Credit Cost)

**What:** Endpoints that serve the dashboard UI directly, authenticated via Supabase JWT instead of API key, with no credit deduction.

**When to use:** Features that enhance the dashboard experience but should not penalize users' credit balance (playground examples, search, coverage browsing).

**Trade-offs:**
- Pro: Users can explore without burning credits
- Pro: Encourages engagement with the platform
- Con: Must be careful about abuse (rate limiting still applies via SlowAPI)
- Con: Different auth path than data endpoints (Supabase JWT vs API key)

**Example:**
```python
# Use get_authenticated_user (existing dependency) instead of require_credits
@router.get("/playground/examples")
async def get_examples(
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Return example markets for playground - no credit cost."""
    # ...
```

### Pattern 4: Client-Side Animation with requestAnimationFrame

**What:** Use the browser's native `requestAnimationFrame` for replay animation rather than pulling in an animation library.

**When to use:** Data-driven animations where frames are discrete state snapshots (tables, charts) rather than continuous DOM/CSS transitions.

**Trade-offs:**
- Pro: Zero additional bundle size
- Pro: Precise timing control (speed multipliers, pause/resume, scrubbing)
- Pro: React state updates only at frame boundaries, minimizing renders
- Con: Must manually manage the animation loop lifecycle
- Con: No built-in easing/spring physics (not needed for data replay)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Per-Frame API Calls

**What people do:** Client calls `/orderbook` once per animation frame during replay.
**Why it's wrong:** 60 frames = 60 API calls = 60 * 5 credits = 300 credits per replay. Latency makes smooth animation impossible. Hammers the database.
**Do this instead:** Single `/replay` endpoint that returns all frames in one response. One API call, one credit charge, all frames client-side.

### Anti-Pattern 2: N+1 Reconstruction Queries

**What people do:** Call `reconstruct_orderbook()` independently for each replay frame, each one finding a snapshot and scanning deltas from scratch.
**Why it's wrong:** Each reconstruction re-scans overlapping delta ranges. For 60 frames over a 1-hour window, you'd scan the same deltas 60 times.
**Do this instead:** Incremental reconstruction -- fetch all deltas once, walk through sequentially, emit frames at target timestamps.

### Anti-Pattern 3: Real-Time Coverage Queries on Partitioned Tables

**What people do:** Run `COUNT(*)` and `MIN(ts)` directly on partitioned snapshots/deltas tables for every coverage page load.
**Why it's wrong:** Partition scanning is expensive. These are analytics queries on OLTP tables.
**Do this instead:** Materialized view, refreshed every 5-15 minutes.

### Anti-Pattern 4: Animation Library for Data Tables

**What people do:** Import framer-motion or react-spring to animate orderbook level changes.
**Why it's wrong:** Adds ~30KB+ to bundle. The "animation" is swapping numbers in a table, not transitioning DOM elements. Animation libraries optimize for layout changes, enter/exit transitions, and spring physics -- none of which apply here.
**Do this instead:** `requestAnimationFrame` loop that updates React state. CSS transitions on bar widths provide the visual smoothness needed.

### Anti-Pattern 5: Mixing Credit-Charged and Free Endpoints

**What people do:** Put playground helper endpoints behind `require_credits()`.
**Why it's wrong:** Users burn credits just browsing the playground, which feels punitive and discourages exploration.
**Do this instead:** Dashboard-internal endpoints authenticated via Supabase JWT (`get_authenticated_user`), with rate limiting but no credit cost. The data endpoints they test still consume credits normally.

---

## Build Order (Dependency-Respecting)

The features have these dependencies:

```
Coverage data (materialized view)
    |
    v
Coverage API endpoints ---------> Coverage dashboard page
    |                                     |
    v                                     v
Playground examples (needs       Sidebar nav update
coverage data for valid timestamps)
    |
    v
Playground form enhancements
    |
    v
Replay service (needs reconstruction.py, coverage for validation)
    |
    v
Replay frontend (needs replay API + orderbook-chart component)
    |
    v
Usage analytics (needs existing key_usage_log data, billing page modification)
```

**Recommended build order:**

1. **Database: materialized view + refresh** -- Foundation for coverage, playground examples, and replay validation
2. **Coverage API + frontend** -- Standalone value, unblocks playground + replay
3. **Playground data population** -- Depends on coverage data for market search + examples
4. **Replay API (backend only)** -- Server-side incremental reconstruction, testable via curl
5. **Replay frontend** -- Visualization + animation, depends on replay API
6. **Usage analytics** -- Independent, can be built in parallel with #4-5

---

## Scaling Considerations

| Concern | Current (100s of markets) | At 10K markets | At 100K+ markets |
|---------|--------------------------|----------------|------------------|
| Coverage view refresh | <1 second | 10-30 seconds | Use `REFRESH CONCURRENTLY`, increase interval |
| Replay frame generation | <500ms for 60 frames | Same (single market) | Same (bounded by market) |
| Replay delta fetch | Fast (daily partitions) | Fast (partition pruning) | Consider archival cutoff |
| Playground search | ILIKE query, fine | Add GIN trigram index | Full-text search |
| Coverage table render | No issues | Virtual scrolling / pagination | Server-side pagination |

The main scaling concern is the materialized view refresh time as data grows. At current scale (hundreds of markets), it's trivial. At 10K+ markets, consider:
- Incremental refresh strategies (only recompute changed markets)
- Separating the view into "hot" (recent data) and "cold" (archived) components
- Moving heavy aggregation to background jobs with pg_cron

---

## Integration Points Summary

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Supabase Postgres | asyncpg pool (existing) | New materialized view, new queries, no new connection patterns |
| Supabase Auth | JWT validation (existing) | Reuse `get_authenticated_user` for dashboard-internal endpoints |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Replay service <-> Reconstruction service | Python function calls | Replay reuses `reconstruct_orderbook` logic (or its internal helpers) |
| Coverage service <-> Markets route | Separate concerns | Coverage reads materialized view; markets route reads raw tables (keep both) |
| Playground routes <-> Coverage service | Direct import | Playground examples use coverage data to find good example markets |
| Frontend api.ts <-> All new endpoints | fetchAPI (existing pattern) | All new endpoints follow existing request/response envelope patterns |

---

## Sources

- Direct codebase analysis: `src/api/routes/*.py`, `src/api/services/*.py`, `src/api/models.py`, `src/api/deps.py`
- Direct codebase analysis: `dashboard/src/components/playground/*.tsx`, `dashboard/src/lib/api.ts`
- Direct codebase analysis: `src/collector/main.py`, `src/collector/discovery.py`, `src/collector/writer.py`
- PostgreSQL materialized views: [PostgreSQL Documentation](https://www.postgresql.org/docs/current/sql-creatematerializedview.html)
- requestAnimationFrame: [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- [Using requestAnimationFrame in React](https://blog.openreplay.com/use-requestanimationframe-in-react-for-smoothest-animations/)
- [FastAPI SSE patterns](https://mahdijafaridev.medium.com/implementing-server-sent-events-sse-with-fastapi-real-time-updates-made-simple-6492f8bfc154) (evaluated but not recommended for v1)
- [react-order-book](https://github.com/lab49/react-order-book) (evaluated but custom implementation preferred for replay animation control)

---
*Architecture research for: KalshiBook Discovery & Replay Features*
*Researched: 2026-02-18*
