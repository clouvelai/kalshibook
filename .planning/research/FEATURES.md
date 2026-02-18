# Feature Research: Discovery & Replay (v1.2)

**Domain:** Market coverage visibility, orderbook replay visualization, and data discovery UX for a prediction market L2 orderbook data API
**Researched:** 2026-02-18
**Confidence:** HIGH (existing codebase reviewed, competitor platforms analyzed, visualization libraries verified, UX patterns confirmed from multiple sources)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users of financial data platforms assume exist when exploring available data and visualizing orderbooks. Missing these makes the product feel like raw infrastructure rather than a usable data service.

| Feature | Why Expected | Complexity | Existing Dependency | Notes |
|---------|--------------|------------|---------------------|-------|
| **Market coverage listing with data ranges** | Every financial data provider (Polygon, Databento, PredictionData.dev) shows which assets have data and for what date ranges. Users must know what is available before they query. Without this, users waste credits on 404s. | LOW | `GET /markets` already returns `first_data_at` / `last_data_at`; `GET /markets/{ticker}` returns `snapshot_count`, `delta_count` | Backend data exists. This is primarily a frontend feature: render the existing `/markets` response as a browsable, filterable table in the dashboard. Add category/status filters, search, and sort. |
| **Market ticker search/autocomplete in playground** | Stripe, Tavily, and every API playground pre-populates with real data. KalshiBook's playground currently requires manually typing ticker strings (e.g., `KXBTC-25FEB14-T96074.99`). Users cannot discover valid tickers from the playground. This is a broken workflow. | MEDIUM | `GET /markets` provides ticker list; playground already has key selection UI via shadcn Combobox pattern | Implement a searchable combobox (shadcn Command + Popover, already in the project) that fetches tickers from `/markets` and lets users search/filter. Debounce search input at 300ms. Show market title alongside ticker for discoverability. |
| **Populated playground examples from real data** | The current `fillExample()` hardcodes `KXBTC-25FEB14-T96074.99` with a fixed timestamp. If this market has no data (or the collector stopped), the example fails. Users see an error on their first interaction. | LOW | `GET /markets` provides real tickers with `first_data_at`/`last_data_at` date ranges | Fetch a handful of markets with known good data on playground load. "Try an example" should pick a market that actually has data and set the timestamp within the available range. Can be a simple server-side endpoint or a client-side heuristic (pick first market from `/markets` with `last_data_at` within the last 24 hours). |
| **Static depth chart visualization (orderbook at one point in time)** | Any platform displaying orderbook data (Binance, Bookmap, TradingView, Highcharts demos) shows depth charts -- the stepped area chart with cumulative bids on one side and asks on the other. The existing playground only shows a raw price/quantity table. Users expect a visual representation. | MEDIUM | `POST /orderbook` returns `yes[]` and `no[]` price levels; `OrderbookPreview` component exists as a table | Build a depth chart component using Recharts (already a sensible choice given the Next.js/React stack). Use `AreaChart` with `type="step"` for the characteristic stepped look. Yes side (green) and No side (red) rendered as opposing cumulative area fills. Prediction market twist: axes are 0-100 cents (probability), not unbounded price. |
| **Data completeness indicator per market** | Users need to know if data is gappy. A market with snapshots but no deltas for 4 hours has a coverage hole. Databento and CoinAPI both surface data quality metrics. Without completeness signals, users cannot trust reconstruction accuracy. | MEDIUM | `snapshot_count` and `delta_count` already returned by `GET /markets/{ticker}`; gap detection requires new query | Add a simple completeness metric: ratio of hours with data vs hours since `first_data_at`. Surface as a percentage or quality badge (Complete / Partial / Sparse) on the market detail view. Exact gap detection (finding specific missing intervals) is a deeper feature -- defer to a later phase. |

### Differentiators (Competitive Advantage)

Features that set KalshiBook apart. Not expected by users, but create compelling value.

| Feature | Value Proposition | Complexity | Existing Dependency | Notes |
|---------|-------------------|------------|---------------------|-------|
| **Animated orderbook replay with timeline scrubber** | The signature feature. No other Kalshi data provider offers a visual, scrubbable replay of orderbook evolution over time. SteelEye charges enterprise pricing for this in traditional finance. TradingView's bar replay is the consumer reference. Users can "watch" how orderbook depth shifted around events (earnings-like moments for prediction markets, like debate outcomes or poll releases). | HIGH | `POST /orderbook` for reconstruction at any timestamp; `POST /deltas` for the stream of changes; `GET /candles/{ticker}` for price overlay | Build a replay engine: (1) Fetch initial orderbook at start time, (2) Fetch deltas for the time range, (3) Apply deltas sequentially to reconstruct orderbook at each point, (4) Animate the depth chart updating over time. Add timeline scrubber (range slider) for play/pause/seek. Add speed controls (1x, 2x, 5x, 10x). Overlay last trade price as a marker. This is the crown jewel feature but also the most complex -- it touches data fetching, client-side reconstruction, animation, and playback controls. |
| **Calendar heatmap of data coverage** | GitHub-contribution-style heatmap showing data density per day per market. At a glance, users see when data collection started, where gaps exist, and which markets have the richest data. No prediction market data provider offers this. PredictionData.dev only lists date ranges. | MEDIUM | `GET /markets` for date ranges; new endpoint needed for per-day data density (count of deltas/snapshots per day) | Requires a new backend endpoint: `GET /markets/{ticker}/coverage` returning daily snapshot/delta counts. Frontend renders as a calendar heatmap using a simple grid of colored cells (Recharts or pure CSS grid with Tailwind colors). Color intensity maps to data density. This is a meaningful differentiator because it immediately communicates data quality and coverage visually. |
| **Price timeline with depth chart overlay** | Show the candle/price chart (like TradingView Lightweight Charts) alongside or below the depth chart replay. Users see price movement and orderbook depth evolution together. This is how professional traders analyze market microstructure. | HIGH | `GET /candles/{ticker}` for OHLCV data; replay engine for depth data | Requires coordinating two visualizations on a shared time axis. TradingView Lightweight Charts is the best option for the price chart (17KB gzipped, canvas-based, 60fps). Sync the timeline scrubber across both charts. This is a v1.3 feature -- build the depth chart replay first, add price overlay later. |
| **Playground multi-endpoint support** | The current playground only supports `POST /orderbook`. A complete playground would support all 10 endpoints: deltas, trades, candles, markets, events, settlements. Each with appropriate form fields and response previews. | MEDIUM | All existing API endpoints; playground architecture (`use-playground.ts`) | Refactor playground from orderbook-specific to endpoint-generic. Add endpoint selector dropdown. Each endpoint has its own form fields (candles need `interval`, deltas need `start_time`/`end_time`, etc.). This increases playground utility significantly and reduces support burden (users can self-serve test all endpoints). |
| **Market grouping by event/series** | Markets in Kalshi are organized hierarchically: Series > Events > Markets. The current `/markets` endpoint returns a flat list. Grouping markets by their parent event (e.g., all "Bitcoin price" markets under one event) makes discovery intuitive. | LOW | `GET /events` and `GET /events/{ticker}` already return event-market hierarchy; `MarketSummary` includes `event_ticker` | Frontend feature: group the market coverage table by `event_ticker`. Collapsible event groups showing child markets. This is a natural UX that leverages existing API data. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but create problems for this milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time live orderbook visualization** | "Show me the orderbook updating live right now." Seems like the obvious companion to replay. | Requires WebSocket infrastructure that does not exist yet (deferred to v2 per PROJECT.md). Building a real-time visualization before the streaming backend exists creates dead UI. Also, Kalshi's own interface shows live orderbooks -- we should not compete with the exchange on live data. | Focus replay on historical data. Label it clearly as "Historical Replay." Add real-time visualization only when WebSocket streaming ships in v2. |
| **Derived metrics in the visualization (spread, imbalance, VWAP)** | Quants want to see computed metrics like bid-ask spread, order imbalance, and volume-weighted average price overlaid on the depth chart. | PROJECT.md explicitly declares derived metrics out of scope: "users compute from raw data." Adding computed metrics to the visualization creates expectations that the API should also serve them, expanding scope. Each metric needs its own definition, edge case handling, and documentation. | Show raw price levels and quantities only. Provide the data cleanly so users can compute their own metrics. Consider adding a "total volume" summary stat as a compromise. |
| **Downloadable replay as video/GIF** | "Let me share this orderbook replay with my team." Recording the visualization as a shareable artifact. | Video encoding in the browser is complex, creates large files, and adds significant implementation complexity for a niche use case. Screen recording tools already exist. | Document that users can use browser screen recording (macOS screen capture, Loom) to share replays. Focus engineering effort on making the replay smooth and useful, not on export. |
| **Full-text search across market rules/descriptions** | "Search for markets about Bitcoin" using free-text search on market rules and metadata. | Requires full-text search infrastructure (Postgres `tsvector` or external search service). The existing `title` and `category` fields provide sufficient filtering for the current market universe. Full-text search is premature optimization for ~1,000 markets. | Filter by category and search by ticker/title substring. The existing market list is small enough that client-side filtering is sufficient. Add full-text search only when the market universe exceeds what client-side filtering handles. |
| **Comparison view (two markets side-by-side)** | Traders want to compare related markets (e.g., two strike prices for the same event). | Doubles the rendering complexity of the replay feature. Each chart needs independent or synchronized timelines. The UX for comparison views is notoriously hard to get right. | Build single-market replay first. Comparison is a v2 feature after the single-market experience is polished. Users can open two browser tabs as a workaround. |

## Feature Dependencies

```
Market Coverage Listing (browsable table)
    |
    +-- Market Ticker Search/Autocomplete in Playground
    |       (search needs the market list to search through)
    |
    +-- Populated Playground Examples
    |       (needs market list to pick a market with real data)
    |
    +-- Data Completeness Indicator
    |       (displayed on market detail, needs coverage data)
    |
    +-- Calendar Heatmap of Data Coverage
    |       (needs new per-day coverage endpoint + market list)
    |
    +-- Market Grouping by Event/Series
            (groups market list by event_ticker)

Static Depth Chart (single-point-in-time visualization)
    |
    +-- Animated Orderbook Replay
            (animates depth chart over time using delta stream)
            |
            +-- requires --> Timeline Scrubber + Playback Controls
            |       (play/pause/seek UI for controlling replay)
            |
            +-- enhanced-by --> Price Timeline Overlay (v1.3+)
                    (candle chart synced to depth chart replay)

Playground Multi-Endpoint Support
    |
    +-- enhanced-by --> Market Ticker Autocomplete
            (ticker search applies to all endpoints, not just orderbook)

Market Ticker Autocomplete
    |
    +-- enhanced-by --> Populated Playground Examples
            (examples use the same market picker)
```

### Dependency Notes

- **Market coverage listing is the foundation:** Nearly every other feature depends on having a browsable, searchable market list. Build this first.
- **Static depth chart must precede animated replay:** The replay feature animates the depth chart component. Build the static version first, verify the visualization is correct, then add animation.
- **Ticker autocomplete enables the playground upgrade:** Once users can search for real tickers, the entire playground becomes useful. This single feature transforms the playground from "developer demo" to "interactive data explorer."
- **Calendar heatmap requires a new backend endpoint:** Unlike other features that leverage existing API endpoints, the heatmap needs per-day data density counts. This is a new query against the partitioned tables.
- **Replay conflicts with real-time:** Do not attempt to build both historical replay and real-time visualization in the same milestone. The architectures are fundamentally different (client-side reconstruction from stored data vs. WebSocket streaming).

## User Workflows

### Workflow 1: "What data do you have?" (Data Discovery)

1. User lands on dashboard, clicks "Markets" or "Data Coverage" in sidebar
2. Sees table of all markets with columns: Ticker, Title, Category, Status, First Data, Last Data, Completeness
3. Filters by category (e.g., "Crypto") or status ("active")
4. Searches for "Bitcoin" -- sees matching markets
5. Clicks a market row to see detail: snapshot/delta counts, data date range, completeness heatmap
6. Decides which market to query based on coverage information

**Existing API support:** `GET /markets` and `GET /markets/{ticker}` provide all data needed except per-day density for heatmap.

### Workflow 2: "Try the API with real data" (Playground)

1. User opens API Playground
2. Selects endpoint from dropdown (Orderbook, Deltas, Trades, Candles, etc.)
3. Types "BTC" in market ticker field -- sees autocomplete dropdown with matching tickers and titles
4. Selects `KXBTC-25FEB14-T96074.99` -- timestamp field auto-populates with a valid time within data range
5. Clicks "Send Request"
6. Sees response JSON, curl command, AND visual preview (depth chart for orderbook, table for trades, candle chart for candles)
7. Adjusts parameters and re-sends

**Existing API support:** All endpoints exist. Playground currently only supports `POST /orderbook`. Ticker autocomplete needs `GET /markets`. Timestamp auto-fill needs `first_data_at`/`last_data_at` from market data.

### Workflow 3: "Watch the orderbook evolve" (Replay)

1. User navigates to replay page (or clicks "Replay" from a market detail page)
2. Selects a market (via autocomplete) and time range
3. Sees static depth chart for the start time
4. Clicks Play -- depth chart animates showing orderbook evolution
5. Uses speed control (1x, 5x, 10x) to watch at different speeds
6. Scrubs timeline to jump to specific moments
7. Pauses to inspect orderbook state at a particular point
8. Sees last trade price marker moving along with the replay

**Existing API support:** `POST /orderbook` for initial state, `POST /deltas` for change stream. Client-side reconstruction logic already exists in `src/api/services/reconstruction.py` (Python) -- needs to be reimplemented in TypeScript for the frontend, or the replay can call the API at regular intervals (simpler but more credit-expensive).

### Workflow 4: "Validate my billing expectations" (Pricing Validation)

1. User reviews their usage dashboard
2. Sees credits consumed per endpoint, per key
3. Can estimate cost of a replay session (X credits for initial orderbook + Y credits per delta page)
4. Adjusts depth parameter or time range to control cost
5. Checks billing page to understand credit costs per operation

**Existing API support:** Billing status, usage tracking, and per-key usage all exist. Pricing validation is about surfacing existing data more clearly and helping users predict costs before making expensive queries.

## Milestone Scope Recommendation

### Phase 1: Market Discovery + Coverage (Foundation)

Build the browsable market coverage table and market detail view. This unblocks everything else.

- [ ] Market coverage page in dashboard (table with filters, search, sort)
- [ ] Market detail panel (snapshot/delta counts, date ranges, metadata)
- [ ] Data completeness badge per market (Complete/Partial/Sparse)
- [ ] Market grouping by event/series (collapsible groups)

### Phase 2: Playground Upgrade (Data Discovery UX)

Transform playground from demo to interactive data explorer.

- [ ] Market ticker autocomplete (shadcn Command + Popover)
- [ ] Populated examples from real market data
- [ ] Multi-endpoint support (all 10 endpoints)
- [ ] Timestamp auto-fill within data range for selected market
- [ ] Endpoint-specific response previews (table for trades, chart for candles)

### Phase 3: Depth Chart + Replay (Signature Feature)

Build the orderbook visualization and replay engine.

- [ ] Static depth chart component (Recharts AreaChart with step interpolation)
- [ ] Client-side orderbook reconstruction in TypeScript (port from Python)
- [ ] Animated replay with delta application
- [ ] Timeline scrubber (range slider with play/pause/seek)
- [ ] Speed controls (1x, 2x, 5x, 10x)
- [ ] Trade price marker overlay

### Phase 4: Coverage Analytics + Pricing (Polish)

Data quality visibility and billing confidence.

- [ ] Calendar heatmap of data coverage (new backend endpoint + frontend)
- [ ] Credit cost estimator for replay sessions
- [ ] Usage breakdown by endpoint in billing dashboard

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Phase |
|---------|------------|---------------------|----------|-------|
| Market coverage table | HIGH | LOW | P1 | 1 |
| Market detail view | HIGH | LOW | P1 | 1 |
| Data completeness badge | MEDIUM | MEDIUM | P1 | 1 |
| Market grouping by event | MEDIUM | LOW | P2 | 1 |
| Ticker autocomplete | HIGH | MEDIUM | P1 | 2 |
| Populated playground examples | HIGH | LOW | P1 | 2 |
| Multi-endpoint playground | MEDIUM | MEDIUM | P2 | 2 |
| Timestamp auto-fill | MEDIUM | LOW | P2 | 2 |
| Static depth chart | HIGH | MEDIUM | P1 | 3 |
| Animated replay | HIGH | HIGH | P1 | 3 |
| Timeline scrubber | HIGH | MEDIUM | P1 | 3 |
| Speed controls | MEDIUM | LOW | P2 | 3 |
| Trade price overlay | MEDIUM | MEDIUM | P2 | 3 |
| Calendar heatmap | MEDIUM | MEDIUM | P2 | 4 |
| Credit cost estimator | LOW | LOW | P3 | 4 |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, include if time permits
- P3: Nice to have, defer if needed

## Competitor Feature Analysis

| Feature | PredictionData.dev | Kalshi (native UI) | Polymarket Analytics | KalshiBook (planned) |
|---------|--------------------|--------------------|----------------------|----------------------|
| **Market listing** | API-only (no UI) | Full UI with search | Dashboard with filters | Browsable table with search, filters, coverage dates |
| **Data coverage visibility** | Date ranges in API response | N/A (live data only) | N/A | Completeness badges + calendar heatmap |
| **Orderbook visualization** | None (CSV export only) | Live depth chart | None | Historical depth chart + animated replay |
| **Orderbook replay** | None | None | None | Timeline scrubber with play/pause/speed control |
| **API playground** | None | None | None | Multi-endpoint with autocomplete + visual previews |
| **Ticker search** | Query by market slug | Full search | Search bar | Autocomplete with market title |
| **Price chart** | None | Live candlestick | Simple line chart | Candle chart in playground (preview), price overlay in replay (future) |

### Key Takeaways

1. **Orderbook replay is a clear differentiator.** No prediction market data provider offers visual, scrubbable orderbook replay. SteelEye offers this for traditional markets at enterprise pricing. KalshiBook can be the first for prediction markets.
2. **Data coverage visibility is underserved.** PredictionData.dev provides date ranges but no quality metrics. Kalshi itself only shows live data. A completeness indicator with calendar heatmap is unique.
3. **Interactive playground is table stakes but nobody does it well for prediction market data.** Kalshi has no playground. PredictionData.dev has no playground. KalshiBook's playground with autocomplete and visual previews would be best-in-class for this niche.
4. **Prediction market depth charts need adaptation.** Traditional depth charts have unbounded price axes. Prediction markets have fixed 0-100 cent range (0-100% probability). The depth chart should reflect this bounded domain with both Yes and No sides visible.

## Technical Considerations for Replay

### Client-side vs. Server-side Reconstruction

**Option A: Server-side (call POST /orderbook at intervals)**
- Simpler implementation: just call the existing API at regular timestamps
- Each reconstruction costs 5 credits
- For a 1-hour replay at 1-second resolution: 3,600 API calls = 18,000 credits
- Too expensive for users. Not viable for fine-grained replay.

**Option B: Client-side reconstruction (fetch deltas, apply in browser)**
- Fetch initial orderbook (5 credits) + fetch all deltas for range (1 credit per page)
- For a 1-hour replay: ~5-50 API calls depending on delta volume
- Requires TypeScript port of the reconstruction logic from `reconstruction.py`
- The reconstruction algorithm is straightforward: maintain yes/no book dicts, apply deltas sequentially
- This is the correct approach. Credit-efficient and enables smooth animation.

**Recommendation:** Client-side reconstruction. The logic is well-defined (snapshot + delta replay) and already implemented in Python. Port to TypeScript. The frontend fetches the initial orderbook and all deltas for the time range, then applies deltas locally to animate the depth chart.

### Depth Chart Design for Prediction Markets

Traditional orderbook depth charts show Bids (left, green) and Asks (right, red) with unbounded price axes. Prediction markets are different:

- **Price range is bounded:** 0-100 cents (representing 0-100% probability)
- **Two sides:** Yes and No, not Bid and Ask
- **Complementary pricing:** Yes at 65c implies No at 35c
- **Visual layout:** Show Yes depth (green, left-to-right from 0-100) and No depth (red, right-to-left from 100-0), meeting near the current implied probability

Use Recharts `AreaChart` with `type="stepAfter"` for the characteristic stepped appearance. The X-axis is 0-100 (price in cents / probability percentage). Y-axis is cumulative quantity. Two series: Yes (green fill) and No (red fill), rendered as opposing areas.

## Sources

### Primary (HIGH confidence -- verified via direct review)
- KalshiBook codebase reviewed: `src/api/routes/markets.py`, `src/api/routes/orderbook.py`, `src/api/services/reconstruction.py`, `dashboard/src/components/playground/*` -- endpoint shapes, reconstruction algorithm, existing UI
- [Highcharts Depth Chart Guide](https://www.highcharts.com/blog/tutorials/depth-chart-a-visual-guide-to-market-liquidity-and-order-flow/) -- depth chart anatomy (bid/ask curves, cumulative volume, step interpolation, area fill)
- [QuestDB Market Replay Systems Glossary](https://questdb.com/glossary/market-replay-systems/) -- replay architecture (data ingestion, time sync, playback controls, analytics output)
- [shadcn/ui Combobox](https://ui.shadcn.com/docs/components/radix/combobox) -- autocomplete component pattern for ticker search
- [Recharts AreaChart API](https://recharts.github.io/en-US/api/Area/) -- step type, animation configuration

### Secondary (MEDIUM confidence -- multiple sources agree)
- [SteelEye Order Book Replay](https://www.steel-eye.com/product-features/order-book-replay) -- enterprise replay feature set (play/pause/rewind/speed control)
- [PredictionData.dev](https://predictiondata.dev) -- competitor offering (tick-level data, CSV export, no visualization)
- [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/docs) -- canvas-based financial charting library (for future price overlay)
- [CoinAPI Order Book Replay Guide](https://www.coinapi.io/blog/crypto-order-book-replay) -- order book replay best practices in crypto
- [Polygon.io](https://polygon.io/) -- market data API with coverage dashboard, usage tracking, ticker search

### Tertiary (LOW confidence -- needs validation during implementation)
- Recharts animation capabilities for smooth depth chart transitions -- may need requestAnimationFrame wrapper for 60fps replay
- Canvas vs SVG performance for orderbook visualization at high update rates -- Recharts uses SVG, may need to switch to Canvas if performance is insufficient for fast replays

---
*Feature research for: Discovery & Replay (KalshiBook v1.2)*
*Researched: 2026-02-18*
