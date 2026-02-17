# Roadmap: KalshiBook

## Overview

KalshiBook delivers a monetized L2 orderbook data API for Kalshi prediction markets. The roadmap moves from data collection (the foundation everything depends on), through API serving with authentication and developer experience, into monetization via Stripe billing, completing the data layer for backtesting viability, and finally a user dashboard for self-service management. Each phase delivers a complete, verifiable capability that unlocks the next. A future milestone will build an agent-first backtesting framework on top of this data layer.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Collection Pipeline** - Persistent websocket collector that captures and stores L2 orderbook data from Kalshi
- [x] **Phase 2: REST API + Authentication** - Serve historical orderbook data via authenticated REST endpoints with developer documentation
- [ ] **Phase 3: Billing + Monetization** - Credit-based pricing with Stripe subscriptions and usage metering
- [ ] **Phase 4: Backtesting-Ready API** - Complete the data layer with trade capture, settlements, candles, and event hierarchy
- [ ] **Phase 5: Dashboard** - Self-service web UI for API key management, usage tracking, and billing
- [ ] **Phase 7: v1 Cleanup & Polish** - Close audit gaps: playground validation, dead code removal, requirements traceability

## Phase Details

### Phase 1: Data Collection Pipeline
**Goal**: Kalshi L2 orderbook data flows reliably into Supabase Postgres with full fidelity -- every snapshot, every delta, every new market discovered and subscribed automatically
**Depends on**: Nothing (first phase)
**Requirements**: DCOL-01, DCOL-02, DCOL-03, DCOL-04, DCOL-05, DCOL-06, DCOL-07, DCOL-08
**Success Criteria** (what must be TRUE):
  1. Collector maintains a persistent websocket connection to Kalshi that automatically reconnects after disconnection
  2. Orderbook snapshots and deltas for subscribed markets are stored in Supabase with accurate timestamps and can be queried via SQL
  3. Sequence gaps on incoming deltas are detected and trigger automatic re-snapshot recovery (no silent data corruption)
  4. New markets appearing on Kalshi are auto-discovered and subscribed to without manual intervention
**Plans**: 1/1 complete

Plans:
- [x] 01-01: Implement collector, storage, and discovery (shipped outside GSD tracking)

### Phase 2: REST API + Authentication
**Goal**: Users can query historical orderbook state, raw deltas, and market metadata through authenticated API endpoints with rate limiting, consistent error handling, and auto-generated documentation
**Depends on**: Phase 1
**Requirements**: DSRV-01, DSRV-02, DSRV-03, DSRV-04, DSRV-05, AUTH-01, AUTH-02, AUTH-03, AUTH-04, DEVX-01, DEVX-02, DEVX-03, DEVX-04
**Success Criteria** (what must be TRUE):
  1. User can request the reconstructed orderbook state for any market at any historical timestamp and receive accurate bid/ask levels
  2. User can query raw orderbook deltas by market and time range with paginated results
  3. User can create an account, generate an API key, and authenticate requests using the X-API-Key header
  4. Requests without a valid API key or exceeding rate limits receive clear, structured error responses with standard rate-limit headers
  5. OpenAPI spec is served at /openapi.json, interactive docs are available, and /llms.txt discovery files exist for AI agents
**Plans**: 3/3 complete

Plans:
- [x] 02-01-PLAN.md — FastAPI app foundation, error handling, Pydantic models, API key migration, auth service
- [x] 02-02-PLAN.md — Data serving endpoints (orderbook reconstruction, deltas, markets)
- [x] 02-03-PLAN.md — Auth proxy, key management, rate limiting, llms.txt

### Phase 3: Billing + Monetization
**Goal**: API access is metered by credits, free tier users get 1,000 credits/month without a credit card, and paid users manage subscriptions through Stripe
**Depends on**: Phase 2
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, BILL-06
**Success Criteria** (what must be TRUE):
  1. Each API operation deducts a defined number of credits and users can see their credit consumption tracked per API key
  2. Free tier users receive 1,000 credits/month and can use the API without entering payment information
  3. Users can upgrade to pay-as-you-go or project tiers via Stripe and their credit allocation adjusts accordingly
  4. When credits are exhausted, further API requests return a clear error message indicating the limit has been reached
**Plans**: 2/2 complete

Plans:
- [x] 03-01-PLAN.md -- Credit metering infrastructure (DB, billing service, require_credits dependency, headers middleware, endpoint integration)
- [x] 03-02-PLAN.md -- Stripe integration (Checkout, Portal, webhooks, PAYG toggle, billing status, llms.txt update)

### Phase 4: Backtesting-Ready API
**Goal**: The data API layer is complete enough for customers to build their own backtesting frameworks -- public trade capture, normalized settlements, candlestick data, and event/market hierarchy are all available through authenticated endpoints
**Depends on**: Phase 3
**Requirements**: BKTS-01, BKTS-02, BKTS-03, BKTS-04
**Success Criteria** (what must be TRUE):
  1. Collector captures public trade executions from the Kalshi `trades` WS channel and trade history is queryable via API with market + time range filtering
  2. Settlement/resolution data is normalized into a queryable format -- users can look up how any market resolved and when
  3. Candlestick/OHLC data is available at 1-minute, 1-hour, and 1-day intervals for any market with captured data
  4. Event/market hierarchy is exposed -- users can query all markets within an event and navigate the Series > Event > Market structure where applicable
**Plans**: 4 plans

Plans:
- [ ] 04-01-PLAN.md -- Database schema (trades, settlements, events, series tables) + API models
- [ ] 04-02-PLAN.md -- Collector extension (trade WS capture, REST enrichment, settlement/event/series data)
- [ ] 04-03-PLAN.md -- API trades + settlements endpoints
- [ ] 04-04-PLAN.md -- API candles + events endpoints + llms.txt update

### Phase 5: Dashboard
**Goal**: Users can manage their KalshiBook account through a self-service web interface -- API keys, usage visibility, and billing management without contacting support
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Logged-in user can view all their API keys, create new keys, and revoke existing keys from the dashboard
  2. User can see their current credit usage and remaining balance for the billing period
  3. User can access Stripe's customer portal to manage their subscription and payment methods
**Plans**: 5 plans

Plans:
- [ ] 05-01-PLAN.md -- Backend gaps (key_type column, per-key usage endpoint, default key on signup)
- [ ] 05-02-PLAN.md -- Next.js 15 scaffolding, Supabase SSR auth, API proxy, login/signup pages
- [ ] 05-03-PLAN.md -- Dashboard layout with sidebar, Overview page (usage bar, PAYG toggle, keys summary)
- [ ] 05-04-PLAN.md -- API Keys management page (CRUD + show-once modal), Billing page (Stripe portal)
- [ ] 05-05-PLAN.md -- End-to-end verification checkpoint

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5
(Sequential execution recommended for solo development)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Collection Pipeline | 1/1 | Complete | 2026-02-13 |
| 2. REST API + Authentication | 3/3 | Complete | 2026-02-14 |
| 3. Billing + Monetization | 2/2 | Complete | 2026-02-14 |
| 4. Backtesting-Ready API | 0/4 | Planned | - |
| 5. Dashboard | 0/5 | Planned | - |
| 7. v1 Cleanup & Polish | 0/1 | Planned | - |

### Phase 6: API Playground

**Goal:** Users can interactively configure, preview, and execute API requests from the dashboard -- with live curl generation, syntax-highlighted responses, and orderbook data preview
**Depends on:** Phase 5
**Plans:** 3 plans

Plans:
- [ ] 06-01-PLAN.md -- Foundation: install deps, sidebar nav, page shell, usePlayground hook, fetch utility
- [ ] 06-02-PLAN.md -- Form panel (key selector, inputs, send button) + code panel (language tabs, syntax-highlighted curl)
- [ ] 06-03-PLAN.md -- Response panel (JSON/Preview tabs, metadata bar, orderbook preview, empty/loading/error states)

### Phase 7: v1 Cleanup & Polish
**Goal:** Close all integration/flow gaps and tech debt from the v1 milestone audit -- playground validation, dead code removal, and requirements traceability update
**Depends on:** Phase 6
**Requirements:** (tech debt closure -- no new requirements)
**Gap Closure:** Closes gaps from v1-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. Playground validates required timestamp field client-side before sending request (no raw 422 errors)
  2. No orphaned dead code remains (PaygToggle component removed, SeriesRecord/SeriesResponse resolved)
  3. REQUIREMENTS.md traceability is current (BKTS-01-04 added, STRM-01/02 moved to v2, Phase 6 coverage noted)
**Plans**: TBD

Plans:
- [ ] 07-01-PLAN.md -- Playground timestamp validation, dead code cleanup, REQUIREMENTS.md traceability update
