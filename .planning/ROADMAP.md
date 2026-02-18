# Roadmap: KalshiBook

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-02-17)
- ✅ **v1.1 Python SDK** — Phases 8-12 (shipped 2026-02-18)
- 🚧 **v1.2 Discovery & Replay** — Phases 13-15 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-02-17</summary>

- [x] Phase 1: Data Collection Pipeline (1/1 plans) — completed 2026-02-13
- [x] Phase 2: REST API + Authentication (3/3 plans) — completed 2026-02-14
- [x] Phase 3: Billing + Monetization (2/2 plans) — completed 2026-02-14
- [x] Phase 4: Backtesting-Ready API (4/4 plans) — completed 2026-02-15
- [x] Phase 5: Dashboard (5/5 plans) — completed 2026-02-16
- [x] Phase 6: API Playground (3/3 plans) — completed 2026-02-16
- [x] Phase 7: v1 Cleanup & Polish (1/1 plan) — completed 2026-02-17

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.1 Python SDK (Phases 8-12) — SHIPPED 2026-02-18</summary>

- [x] Phase 8: SDK Scaffolding (1/1 plans) — completed 2026-02-17
- [x] Phase 9: Models, Exceptions, and HTTP Transport (3/3 plans) — completed 2026-02-17
- [x] Phase 10: Client Class and Data Endpoints (2/2 plans) — completed 2026-02-17
- [x] Phase 11: Pagination and DataFrame Support (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Documentation and PyPI Publishing (3/3 plans) — completed 2026-02-18

See [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) for full details.

</details>

### 🚧 v1.2 Discovery & Replay (In Progress)

**Milestone Goal:** Make the API foundation production-ready and compelling -- users can discover available market data, see real tickers in the playground, and visually explore orderbook depth at any covered timestamp.

- [ ] **Phase 13: Market Coverage Discovery** — Browsable, searchable market coverage with pre-computed segment stats
- [ ] **Phase 14: Playground Upgrade** — Real tickers, autocomplete, example cards, and zero-credit demos
- [ ] **Phase 15: Depth Chart Visualization** — Canvas-rendered orderbook depth chart embedded in the playground

## Phase Details

### Phase 13: Market Coverage Discovery
**Goal**: Users can discover which markets have data, how much, and where the gaps are
**Depends on**: Phase 12 (v1.1 complete)
**Requirements**: COVR-01, COVR-02, COVR-03, COVR-04, COVR-05
**Success Criteria** (what must be TRUE):
  1. User can view a paginated table of all markets with data, showing contiguous coverage segments (date ranges with gap boundaries) for each
  2. User can see per-market summary stats (total data points, segment count, snapshot/delta/trade counts) that load in under 2 seconds
  3. User can search markets by ticker substring and filter by event or active/settled status, with results updating as they type
  4. Coverage stats are served from a pre-computed materialized view, not live partition scans
  5. Coverage segments reflect actual data gaps -- a market with data on days 1-3 and 7-10 shows two segments, not one range of 1-10
**Plans:** 2 plans

Plans:
- [ ] 13-01-PLAN.md -- Materialized view migration + FastAPI coverage endpoint + response models
- [ ] 13-02-PLAN.md -- Coverage dashboard page with table, search, filters, timeline bars, summary cards

### Phase 14: Playground Upgrade
**Goal**: Users can explore the API through the playground without guessing tickers or burning credits
**Depends on**: Phase 13
**Requirements**: PLAY-01, PLAY-02, PLAY-03, PLAY-04
**Success Criteria** (what must be TRUE):
  1. Playground ticker input pre-populates from real captured markets (not hardcoded values that break when markets settle)
  2. User can type partial ticker text and get autocomplete suggestions from markets with confirmed data coverage
  3. Playground shows example cards with pre-populated queries for common use cases (orderbook reconstruction, trade history, candles) that execute with one click
  4. All playground demo interactions cost zero credits -- served via dashboard-internal endpoint or pre-baked responses, not through the billed API path
**Plans**: TBD

Plans:
- [ ] 14-01: TBD
- [ ] 14-02: TBD

### Phase 15: Depth Chart Visualization
**Goal**: Users can visually inspect orderbook depth at any covered timestamp, rendered as a Canvas-based chart in the playground
**Depends on**: Phase 14
**Requirements**: DPTH-01, DPTH-02, DPTH-03, PLAY-05
**Success Criteria** (what must be TRUE):
  1. User can view a depth chart showing Yes and No sides across the 0-100 cent price range for any market at any covered timestamp
  2. Depth chart renders using HTML Canvas (not SVG) to support future animation without a rewrite
  3. Depth chart is accessible as a tab in the playground alongside the existing API response view
  4. Selecting a different market or timestamp in the playground updates the depth chart accordingly
**Plans**: TBD

Plans:
- [ ] 15-01: TBD
- [ ] 15-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 13 → 14 → 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Collection Pipeline | v1.0 | 1/1 | Complete | 2026-02-13 |
| 2. REST API + Authentication | v1.0 | 3/3 | Complete | 2026-02-14 |
| 3. Billing + Monetization | v1.0 | 2/2 | Complete | 2026-02-14 |
| 4. Backtesting-Ready API | v1.0 | 4/4 | Complete | 2026-02-15 |
| 5. Dashboard | v1.0 | 5/5 | Complete | 2026-02-16 |
| 6. API Playground | v1.0 | 3/3 | Complete | 2026-02-16 |
| 7. v1 Cleanup & Polish | v1.0 | 1/1 | Complete | 2026-02-17 |
| 8. SDK Scaffolding | v1.1 | 1/1 | Complete | 2026-02-17 |
| 9. Models, Exceptions, HTTP Transport | v1.1 | 3/3 | Complete | 2026-02-17 |
| 10. Client Class & Data Endpoints | v1.1 | 2/2 | Complete | 2026-02-17 |
| 11. Pagination & DataFrame Support | v1.1 | 2/2 | Complete | 2026-02-17 |
| 12. Documentation & PyPI Publishing | v1.1 | 3/3 | Complete | 2026-02-18 |
| 13. Market Coverage Discovery | v1.2 | 0/? | Not started | - |
| 14. Playground Upgrade | v1.2 | 0/? | Not started | - |
| 15. Depth Chart Visualization | v1.2 | 0/? | Not started | - |
