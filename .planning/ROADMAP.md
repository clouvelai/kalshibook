# Roadmap: KalshiBook

## Overview

KalshiBook delivers a monetized L2 orderbook data API for Kalshi prediction markets. The roadmap moves from data collection (the foundation everything depends on), through API serving with authentication and developer experience, into monetization via Stripe billing, real-time streaming for live traders, and finally a user dashboard for self-service management. Each phase delivers a complete, verifiable capability that unlocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Collection Pipeline** - Persistent websocket collector that captures and stores L2 orderbook data from Kalshi
- [x] **Phase 2: REST API + Authentication** - Serve historical orderbook data via authenticated REST endpoints with developer documentation
- [ ] **Phase 3: Billing + Monetization** - Credit-based pricing with Stripe subscriptions and usage metering
- [ ] **Phase 4: Real-Time Streaming** - Live orderbook updates via websocket for subscribers
- [ ] **Phase 5: Dashboard** - Self-service web UI for API key management, usage tracking, and billing

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

### Phase 4: Real-Time Streaming
**Goal**: Users can subscribe to live orderbook updates via websocket for real-time trading strategy execution
**Depends on**: Phase 2
**Requirements**: STRM-01, STRM-02
**Success Criteria** (what must be TRUE):
  1. User can open a websocket connection, authenticate with a valid API key, and subscribe to orderbook updates for specific markets
  2. Subscribed users receive orderbook updates in real time as the collector ingests them from Kalshi
  3. Unauthenticated or invalid websocket connections are rejected with a clear error on handshake
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Dashboard
**Goal**: Users can manage their KalshiBook account through a self-service web interface -- API keys, usage visibility, and billing management without contacting support
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Logged-in user can view all their API keys, create new keys, and revoke existing keys from the dashboard
  2. User can see their current credit usage and remaining balance for the billing period
  3. User can access Stripe's customer portal to manage their subscription and payment methods
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5
(Note: Phases 4 and 5 have different dependencies -- Phase 4 depends on Phase 2, Phase 5 depends on Phase 3 -- but sequential execution is recommended for solo development)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Collection Pipeline | 1/1 | Complete | 2026-02-13 |
| 2. REST API + Authentication | 3/3 | Complete | 2026-02-14 |
| 3. Billing + Monetization | 2/2 | Complete | 2026-02-14 |
| 4. Real-Time Streaming | 0/TBD | Not started | - |
| 5. Dashboard | 0/TBD | Not started | - |
