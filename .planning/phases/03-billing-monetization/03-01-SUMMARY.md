---
phase: 03-billing-monetization
plan: 01
subsystem: billing
tags: [stripe, credits, metering, asyncpg, middleware]

# Dependency graph
requires:
  - phase: 02-api-auth
    provides: "API key auth (get_api_key dependency), data endpoints (orderbook, deltas, markets), asyncpg pool"
provides:
  - "billing_accounts table with tier/credits/PAYG/Stripe mapping"
  - "api_key_usage table for per-key usage tracking"
  - "billing service (ensure_billing_account, deduct_credits, lazy_reset_credits, log_key_usage, report_stripe_usage)"
  - "require_credits(cost) dependency factory chaining after get_api_key"
  - "CreditsExhaustedError (429) with upgrade message"
  - "Credit headers middleware (X-Credits-Remaining/Used/Total/Cost)"
  - "Billing response models (BillingStatusResponse, PaygToggleRequest, CheckoutResponse, PortalResponse)"
  - "Stripe SDK initialized in lifespan"
affects: [03-02-PLAN, billing-routes, stripe-webhooks]

# Tech tracking
tech-stack:
  added: [stripe>=14.0.0]
  patterns: [dependency-factory-chaining, fire-and-forget-asyncio-tasks, lazy-upsert-on-first-request, atomic-credit-deduction]

key-files:
  created:
    - supabase/migrations/20260215000001_create_billing_accounts.sql
    - supabase/migrations/20260215000002_create_api_key_usage.sql
    - src/api/services/billing.py
  modified:
    - src/api/deps.py
    - src/api/main.py
    - src/api/errors.py
    - src/api/models.py
    - src/shared/config.py
    - src/api/routes/orderbook.py
    - src/api/routes/deltas.py
    - src/api/routes/markets.py
    - pyproject.toml

key-decisions:
  - "Rate limiter set to 120/minute backstop; credit system is real enforcement (avoids SlowAPI tier-awareness complexity)"
  - "Billing accounts created lazily on first API request via ensure_billing_account upsert"
  - "PAYG overage and usage logging use asyncio.create_task fire-and-forget to avoid blocking request path"

patterns-established:
  - "Dependency factory chaining: require_credits(cost) wraps get_api_key via Depends"
  - "Fire-and-forget tasks: asyncio.create_task for non-critical side effects (usage log, Stripe meter)"
  - "Lazy upsert: billing account created on first request, not at signup"
  - "Atomic credit deduction: single UPDATE with WHERE guard prevents overdraft (unless PAYG)"

# Metrics
duration: 3min
completed: 2026-02-14
---

# Phase 3 Plan 1: Credit Metering Summary

**Atomic credit deduction with lazy billing accounts, per-key usage tracking, PAYG overage to Stripe, and X-Credits headers on every response**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-14T20:34:22Z
- **Completed:** 2026-02-14T20:38:20Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Every data endpoint deducts credits atomically via require_credits dependency (orderbook=5, deltas=2, markets=1)
- Free-tier users get 1,000 credits/month, billing accounts created lazily on first API request
- Credits exhausted returns 429 CreditsExhaustedError with clear upgrade guidance
- PAYG users can exceed allocation; overage reported to Stripe Billing Meter API
- Per-key usage tracked in api_key_usage table (endpoint + credits_charged)
- Credit info in response headers (X-Credits-Remaining, X-Credits-Used, X-Credits-Total, X-Credits-Cost)
- Monthly credit reset works: lazy_reset_credits checks billing_cycle_start and resets atomically

## Task Commits

Each task was committed atomically:

1. **Task 1: Database schema, billing service, and configuration** - `8323979` (feat)
2. **Task 2: Credit dependency, headers middleware, tier-aware rate limits, and endpoint integration** - `3690159` (feat)

## Files Created/Modified
- `supabase/migrations/20260215000001_create_billing_accounts.sql` - Billing accounts table (tier, credits, PAYG, Stripe mapping)
- `supabase/migrations/20260215000002_create_api_key_usage.sql` - Per-API-key usage tracking table
- `src/api/services/billing.py` - Billing service: ensure_billing_account, deduct_credits, lazy_reset_credits, log_key_usage, report_stripe_usage
- `src/api/deps.py` - require_credits(cost) dependency factory, CREDIT_COSTS, TIER_RATE_LIMITS constants
- `src/api/main.py` - Credit headers middleware, Stripe init in lifespan, rate limiter 120/min backstop
- `src/api/errors.py` - CreditsExhaustedError (429)
- `src/api/models.py` - BillingStatusResponse, PaygToggleRequest/Response, CheckoutResponse, PortalResponse
- `src/shared/config.py` - Stripe config fields (secret_key, webhook_secret, project_price_id, meter_event_name, app_url)
- `src/api/routes/orderbook.py` - Depends(require_credits(5))
- `src/api/routes/deltas.py` - Depends(require_credits(2))
- `src/api/routes/markets.py` - Depends(require_credits(1))
- `pyproject.toml` - Added stripe>=14.0.0 dependency

## Decisions Made
- **Rate limiter as backstop:** Set to 120/minute (Project-tier max) since credit system enforces real limits. SlowAPI can't easily do tier-aware limits because it evaluates before dependency injection runs. Free users with 1000 credits/month will exhaust credits well before rate limits matter.
- **Lazy billing accounts:** Created on first API request via upsert, not at signup. Avoids coupling signup flow to billing and handles existing users gracefully.
- **Fire-and-forget for side effects:** Usage logging and Stripe meter reporting use asyncio.create_task to avoid blocking the request path. Failures are logged but don't affect the API response.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**External services require manual configuration for Stripe integration (Plan 03-02).**

Environment variables needed before Stripe features work:
- `STRIPE_SECRET_KEY` - Stripe Dashboard -> Developers -> API keys -> Secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe Dashboard -> Developers -> Webhooks -> Signing secret
- `STRIPE_PROJECT_PRICE_ID` - Stripe Dashboard -> Product catalog -> Price ID
- `STRIPE_METER_EVENT_NAME` - Stripe Dashboard -> Billing -> Meters -> Event name (default: kalshibook_api_credits)

Note: Credit metering works locally without Stripe configured. Stripe reporting is gracefully skipped when stripe_secret_key is empty.

## Next Phase Readiness
- Credit metering infrastructure complete; ready for Plan 03-02 (Stripe checkout, webhooks, billing routes)
- All data endpoints integrated with require_credits
- Billing models ready for billing API routes
- Stripe SDK installed and initialized in lifespan

## Self-Check: PASSED

All 11 key files verified present. Both task commits (8323979, 3690159) confirmed in git log.

---
*Phase: 03-billing-monetization*
*Completed: 2026-02-14*
