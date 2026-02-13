# Requirements: KalshiBook

**Defined:** 2026-02-13
**Core Value:** Reliable, complete orderbook history for every Kalshi market — reconstructable to any point in time

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Collection

- [ ] **DCOL-01**: System connects to Kalshi websocket and maintains persistent connection with automatic reconnection
- [ ] **DCOL-02**: System subscribes to orderbook channel for active/liquid Kalshi markets
- [ ] **DCOL-03**: System receives and stores initial orderbook snapshot per market with timestamp
- [ ] **DCOL-04**: System receives and stores all subsequent orderbook deltas with timestamps
- [ ] **DCOL-05**: System validates sequence numbers on every delta and detects gaps
- [ ] **DCOL-06**: System triggers re-snapshot when sequence gap detected (recovery)
- [ ] **DCOL-07**: System auto-discovers new markets via market lifecycle websocket channel
- [ ] **DCOL-08**: System auto-subscribes to newly discovered active markets

### Data Serving

- [ ] **DSRV-01**: User can query reconstructed orderbook state at any historical timestamp for a given market
- [ ] **DSRV-02**: User can query raw orderbook deltas by market and time range (paginated)
- [ ] **DSRV-03**: User can list available markets with data coverage dates
- [ ] **DSRV-04**: User can query market metadata (event info, contract specs)
- [ ] **DSRV-05**: All API responses use consistent JSON format with structured error envelope

### Real-time Streaming

- [ ] **STRM-01**: User can subscribe to real-time orderbook updates via websocket
- [ ] **STRM-02**: Streaming requires valid API key authentication on connect

### Authentication & Access Control

- [ ] **AUTH-01**: User can create account (email/password via Supabase Auth)
- [ ] **AUTH-02**: User can generate API keys from dashboard
- [ ] **AUTH-03**: API validates `X-API-Key` header on every request
- [ ] **AUTH-04**: Per-key rate limiting enforced with standard response headers

### Billing & Monetization

- [ ] **BILL-01**: Credit-based pricing: each API operation costs defined credits
- [ ] **BILL-02**: Free tier: 1,000 credits/month (no credit card required)
- [ ] **BILL-03**: Pay-as-you-go tier via Stripe
- [ ] **BILL-04**: Project tier with monthly credit allocation via Stripe
- [ ] **BILL-05**: Usage metering tracks credits consumed per API key
- [ ] **BILL-06**: Access blocked when credits exhausted (with clear error message)

### Developer Experience

- [ ] **DEVX-01**: OpenAPI 3.1 spec auto-generated and served at `/openapi.json`
- [ ] **DEVX-02**: API documentation page hosted (Swagger/Redoc)
- [ ] **DEVX-03**: `/llms.txt` and `/llms-full.txt` discovery files for AI agents
- [ ] **DEVX-04**: Agent-friendly response design (flat JSON, natural language field names, contextual metadata)

### Dashboard

- [ ] **DASH-01**: User can view and manage API keys (create, revoke)
- [ ] **DASH-02**: User can view current usage and remaining credits
- [ ] **DASH-03**: User can manage billing (link to Stripe customer portal)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### SDKs

- **SDK-01**: Python SDK auto-generated from OpenAPI spec
- **SDK-02**: TypeScript SDK auto-generated from OpenAPI spec
- **SDK-03**: JavaScript SDK auto-generated from OpenAPI spec

### Advanced Features

- **ADV-01**: MCP server exposing KalshiBook endpoints as AI agent tools
- **ADV-02**: Downloadable flat files (CSV/Parquet) for bulk backtesting
- **ADV-03**: Enterprise tier with custom rate limits and SLAs
- **ADV-04**: Public trades capture via websocket

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Trade execution / order placement | Read-only data product, not a brokerage |
| Multi-exchange aggregation (Polymarket, Manifold) | Deep on Kalshi first |
| OHLCV candle aggregation | Prediction markets don't fit candle model; Kalshi REST already has this |
| GraphQL API | REST-only, better for agents, simpler to rate-limit |
| Mobile app | Web dashboard + API only |
| Connection pooling / multi-WS redundancy | Future milestone after validating PMF |
| Derived metrics (spread, mid-price, order imbalance) | Users compute from raw data |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DCOL-01 | — | Pending |
| DCOL-02 | — | Pending |
| DCOL-03 | — | Pending |
| DCOL-04 | — | Pending |
| DCOL-05 | — | Pending |
| DCOL-06 | — | Pending |
| DCOL-07 | — | Pending |
| DCOL-08 | — | Pending |
| DSRV-01 | — | Pending |
| DSRV-02 | — | Pending |
| DSRV-03 | — | Pending |
| DSRV-04 | — | Pending |
| DSRV-05 | — | Pending |
| STRM-01 | — | Pending |
| STRM-02 | — | Pending |
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| AUTH-03 | — | Pending |
| AUTH-04 | — | Pending |
| BILL-01 | — | Pending |
| BILL-02 | — | Pending |
| BILL-03 | — | Pending |
| BILL-04 | — | Pending |
| BILL-05 | — | Pending |
| BILL-06 | — | Pending |
| DEVX-01 | — | Pending |
| DEVX-02 | — | Pending |
| DEVX-03 | — | Pending |
| DEVX-04 | — | Pending |
| DASH-01 | — | Pending |
| DASH-02 | — | Pending |
| DASH-03 | — | Pending |

**Coverage:**
- v1 requirements: 32 total
- Mapped to phases: 0
- Unmapped: 32 ⚠️

---
*Requirements defined: 2026-02-13*
*Last updated: 2026-02-13 after initial definition*
