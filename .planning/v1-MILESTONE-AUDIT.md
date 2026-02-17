---
milestone: v1.0
audited: 2026-02-17T01:50:00Z
status: tech_debt
scores:
  requirements: 30/32
  phases: 4/6 verified (2 missing VERIFICATION.md)
  integration: 10/13 wiring points connected
  flows: 4/5 E2E flows complete
gaps:
  requirements:
    - "STRM-01: User can subscribe to real-time orderbook updates via websocket — not implemented (Phase 4 re-scoped to backtesting)"
    - "STRM-02: Streaming requires valid API key authentication on connect — not implemented (Phase 4 re-scoped to backtesting)"
  integration:
    - "Playground timestamp validation: POST /orderbook requires timestamp field but playground allows submission without it (422 error instead of client-side validation)"
  flows:
    - "Playground flow without timestamp: user fills ticker, leaves timestamp blank, gets confusing 422 instead of client-side validation message"
tech_debt:
  - phase: 01-data-collection-pipeline
    items:
      - "No VERIFICATION.md — shipped outside GSD tracking, no formal verification performed"
  - phase: 03-billing-monetization
    items:
      - "No VERIFICATION.md — plans completed and self-checked but formal verification never run"
      - "No billing-specific tests — deferred until test infrastructure built"
  - phase: 05-dashboard
    items:
      - "PaygToggle component is orphaned dead code (PAYG toggle functionality lives in UsageBar instead)"
      - "5 human verification scenarios documented but only partially validated"
  - phase: 06-api-playground
    items:
      - "Playground sends request without validating required timestamp field"
      - "Python/JS code generation tabs disabled (Coming soon)"
  - phase: 04-backtesting-ready-api
    items:
      - "SeriesRecord/SeriesResponse Pydantic models defined but no /series API route exists"
      - "BKTS-01 through BKTS-04 requirements used in roadmap but never added to REQUIREMENTS.md traceability"
---

# v1.0 Milestone Audit Report

**Milestone:** KalshiBook v1.0
**Audited:** 2026-02-17
**Status:** tech_debt (all core functionality works, 2 requirements deferred, accumulated tech debt)

## Milestone Definition of Done

From ROADMAP.md: KalshiBook delivers a monetized L2 orderbook data API for Kalshi prediction markets. The roadmap covers data collection, API serving with authentication, monetization via Stripe, backtesting data layer, user dashboard, and API playground.

## Phase Verification Summary

| Phase | Name | Plans | Verified | Status |
|-------|------|-------|----------|--------|
| 1 | Data Collection Pipeline | 1/1 | No VERIFICATION.md | Shipped outside GSD |
| 2 | REST API + Authentication | 3/3 | 2026-02-14 | PASSED (5/5 truths) |
| 3 | Billing + Monetization | 2/2 | No VERIFICATION.md | Plans self-checked |
| 4 | Backtesting-Ready API | 4/4 | 2026-02-15 | PASSED (4/4 truths) |
| 5 | Dashboard | 5/5 | 2026-02-16 | PASSED (3/3 truths, human_needed) |
| 6 | API Playground | 3/3 | 2026-02-16 | PASSED (7/7 truths) |

**Total:** 16/16 plans completed across 6 phases. 4/6 phases formally verified.

## Requirements Coverage

### Satisfied (30/32)

| Requirement | Phase | Evidence |
|-------------|-------|----------|
| DCOL-01: Persistent WS connection with reconnection | 1 | Collector code exists in `src/collector/connection.py` |
| DCOL-02: Subscribe to orderbook channel for active markets | 1 | `src/collector/main.py` WS subscription |
| DCOL-03: Store initial orderbook snapshot with timestamp | 1 | `src/collector/writer.py` snapshot flush |
| DCOL-04: Store all subsequent deltas with timestamps | 1 | `src/collector/writer.py` delta flush |
| DCOL-05: Validate sequence numbers, detect gaps | 1 | `src/collector/processor.py` sequence validation |
| DCOL-06: Re-snapshot on sequence gap | 1 | Recovery logic in collector |
| DCOL-07: Auto-discover new markets via lifecycle WS | 1 | `src/collector/discovery.py` |
| DCOL-08: Auto-subscribe to newly discovered markets | 1 | `src/collector/main.py` discovery integration |
| DSRV-01: Query reconstructed orderbook at timestamp | 2 | POST /orderbook with reconstruction service |
| DSRV-02: Query raw deltas by market and time range | 2 | POST /deltas with cursor pagination |
| DSRV-03: List markets with data coverage dates | 2 | GET /markets |
| DSRV-04: Query market metadata | 2 | GET /markets/{ticker} |
| DSRV-05: Consistent JSON error envelope | 2 | Error handlers in `src/api/errors.py` |
| AUTH-01: Create account via Supabase Auth | 2 | POST /auth/signup |
| AUTH-02: Generate API keys from dashboard | 2+5 | POST /keys + dashboard keys page |
| AUTH-03: Validate X-API-Key header | 2 | `get_api_key` dependency in `deps.py` |
| AUTH-04: Per-key rate limiting with headers | 2 | SlowAPI + credit headers middleware |
| DEVX-01: OpenAPI 3.1 at /openapi.json | 2 | FastAPI auto-serves |
| DEVX-02: Swagger/Redoc docs | 2 | /docs and /redoc routes |
| DEVX-03: /llms.txt discovery files | 2 | Dedicated routes for llms.txt and llms-full.txt |
| DEVX-04: Agent-friendly response design | 2 | Flat JSON, request_id, response_time |
| BILL-01: Credit-based pricing per operation | 3 | `require_credits(cost)` on all data endpoints |
| BILL-02: Free tier 1,000 credits/month | 3 | Default billing account with 1000 credits |
| BILL-03: PAYG tier via Stripe | 3 | PAYG toggle + Stripe meter reporting |
| BILL-04: Project tier with monthly allocation | 3 | Stripe Checkout for $30/mo, 4000 credits |
| BILL-05: Usage metering per API key | 3 | `api_key_usage` table + `log_key_usage` |
| BILL-06: Block on credits exhausted | 3 | `CreditsExhaustedError` (429) |
| DASH-01: View and manage API keys | 5 | Keys page with CRUD |
| DASH-02: View usage and remaining credits | 5 | Overview UsageBar + Billing page |
| DASH-03: Manage billing via Stripe portal | 5 | Stripe portal/checkout buttons |

### Unsatisfied (2/32)

| Requirement | Phase | Status | Notes |
|-------------|-------|--------|-------|
| STRM-01: Subscribe to real-time orderbook updates via WS | 4 | NOT IMPLEMENTED | Phase 4 re-scoped from streaming to backtesting (BKTS-01-04). No user-facing WebSocket server exists. |
| STRM-02: Streaming requires valid API key auth on connect | 4 | NOT IMPLEMENTED | Depends on STRM-01. No WS server to authenticate against. |

**Assessment:** STRM-01/02 were deprioritized when Phase 4 was re-scoped to "Backtesting-Ready API". The product is fully functional without real-time streaming. These should be moved to v2 requirements or tracked as a future phase.

### Bonus (not in original requirements)

Phase 4 implemented BKTS-01 through BKTS-04 (trade capture, settlements, candles, event hierarchy) which were defined in the roadmap but never added to REQUIREMENTS.md. Phase 6 (API Playground) was added after initial requirements.

## Cross-Phase Integration Report

### Wiring Points (10/13 connected)

| Wiring Point | Status |
|---|---|
| Collector tables → API queries (6 tables) | CONNECTED |
| get_api_key → require_credits chain | CONNECTED |
| All 10 data endpoints → require_credits | CONNECTED |
| Billing endpoints → JWT auth | CONNECTED |
| Dashboard fetchAPI → Supabase JWT | CONNECTED |
| Next.js proxy /api/* → :8000/* | CONNECTED |
| Dashboard middleware auth guard | CONNECTED |
| Signup → billing account + default key | CONNECTED |
| Playground → api.keys.reveal() | CONNECTED |
| Billing dashboard → all 4 billing APIs | CONNECTED |
| PaygToggle component | ORPHANED |
| SeriesRecord/SeriesResponse models | ORPHANED |
| Playground timestamp validation | BROKEN |

### E2E User Flows (4/5 complete)

| Flow | Status | Notes |
|------|--------|-------|
| New User: Signup → default key → usage → API requests | COMPLETE | Silent-fail recovery via lazy-init |
| API Consumer: Login → create key → query data → credits deducted | COMPLETE | All 10 endpoints guarded |
| Upgrade: Free → credits exhausted → Stripe Checkout → more credits | COMPLETE | Webhook updates tier |
| Key Management: Create → copy → use → see usage → revoke | COMPLETE | Show-once modal pattern |
| Playground: Login → select key → enter ticker → send → response | PARTIAL | Works via "Try Example" but no client-side validation for required timestamp field |

## Tech Debt Summary

### Phase 1: Data Collection Pipeline
- No formal verification (shipped before GSD tracking)

### Phase 3: Billing + Monetization
- No formal VERIFICATION.md
- No billing-specific tests

### Phase 4: Backtesting-Ready API
- `SeriesRecord`/`SeriesResponse` Pydantic models defined but no `/series` API route
- BKTS-01-04 requirements used in roadmap but not in REQUIREMENTS.md traceability

### Phase 5: Dashboard
- `PaygToggle` component is orphaned dead code (functionality lives in `UsageBar`)
- 5 human verification scenarios partially validated

### Phase 6: API Playground
- No client-side validation for required `timestamp` field (sends invalid request, gets 422)
- Python/JS code generation tabs disabled (Coming soon)

### Cross-cutting
- STRM-01/02 requirements need to be moved to v2 or tracked as future phase
- REQUIREMENTS.md traceability table is stale (doesn't reflect Phase 4 re-scope or Phase 6 addition)

**Total: 12 tech debt items across 6 phases**

## Conclusion

The v1.0 milestone delivers a **functional, end-to-end monetized API product** covering:
- Real-time data collection from Kalshi WebSocket
- 10 authenticated REST endpoints with credit metering
- Stripe billing with free/PAYG/Project tiers
- Self-service dashboard with key management, usage, billing
- Interactive API playground

**30/32 v1 requirements are satisfied.** The 2 unsatisfied requirements (real-time streaming) were consciously deprioritized when Phase 4 was re-scoped. All critical user flows work end-to-end.

The accumulated tech debt is non-blocking and can be addressed in a future cleanup phase or v2 milestone.

---

_Audited: 2026-02-17T01:50:00Z_
_Auditor: Claude (gsd-audit-milestone)_
