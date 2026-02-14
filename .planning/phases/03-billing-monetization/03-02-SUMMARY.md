---
phase: 03-billing-monetization
plan: 02
subsystem: billing
tags: [stripe, checkout, webhooks, portal, payg, billing-routes, llms-txt]

# Dependency graph
requires:
  - phase: 03-billing-monetization
    plan: 01
    provides: "billing_accounts table, billing service (ensure/deduct/reset credits), require_credits dependency, Stripe SDK init, billing response models"
  - phase: 02-api-auth
    provides: "API key auth, data endpoints, Supabase JWT auth (get_authenticated_user), asyncpg pool"
provides:
  - "Billing routes: GET /billing/status, POST /billing/checkout, POST /billing/portal, POST /billing/payg, POST /billing/webhook"
  - "Stripe Checkout integration for Project plan upgrades ($30/month, 4,000 credits)"
  - "Stripe Customer Portal for subscription management (cancel, update payment)"
  - "Webhook handler for subscription lifecycle: created, updated, deleted, payment_failed"
  - "PAYG toggle endpoint with automatic Stripe customer creation"
  - "Billing service functions: sync_subscription_state, handle_subscription_canceled, handle_payment_failed, get_billing_status, toggle_payg, update_stripe_customer_id"
  - "Updated llms.txt with billing section (credit costs, tiers, endpoints)"
  - "Updated llms-full.txt with comprehensive billing docs (tier comparison, headers, exhaustion, agent upgrade flow, error codes)"
affects: [llms-txt, ai-discovery, phase-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [stripe-checkout-flow, webhook-signature-verification, customer-portal-session, idempotent-webhook-handlers]

key-files:
  created:
    - src/api/routes/billing.py
  modified:
    - src/api/services/billing.py
    - src/api/main.py
    - static/llms.txt
    - static/llms-full.txt

key-decisions:
  - "Billing endpoints use Supabase JWT auth (not API keys) since they manage account-level state, not data queries"
  - "Webhook handler is idempotent: sync_subscription_state handles all subscription statuses (active, past_due, canceled)"
  - "Payment failures are logged but do not immediately downgrade tier; Stripe retries and eventually sends subscription.deleted"
  - "PAYG toggle auto-creates Stripe customer if none exists, reducing friction for enabling overage billing"

patterns-established:
  - "Stripe Checkout flow: create customer if needed -> create checkout session -> redirect user -> webhook updates state"
  - "Webhook signature verification: raw body + stripe-signature header -> construct_event"
  - "Idempotent webhook handlers: lookup by stripe_customer_id, graceful handling of missing records"

# Metrics
duration: 2min
completed: 2026-02-14
---

# Phase 3 Plan 2: Stripe Billing Routes Summary

**Stripe Checkout for plan upgrades, Customer Portal for subscription management, webhook handler for lifecycle events, PAYG toggle, and AI discovery docs with full billing reference**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-14T21:30:35Z
- **Completed:** 2026-02-14T21:32:23Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Five billing endpoints: GET /billing/status, POST /billing/checkout, POST /billing/portal, POST /billing/payg, POST /billing/webhook
- Stripe Checkout integration: users upgrade to Project plan ($30/month, 4,000 credits) via hosted checkout page
- Webhook handler processes subscription lifecycle (created, updated, deleted, payment_failed) idempotently
- PAYG toggle with automatic Stripe customer creation for frictionless overage billing
- llms.txt updated with billing section covering credit costs, tiers, and billing endpoints
- llms-full.txt expanded with 150+ lines of billing documentation: credit system overview, tier comparison table, response headers, credit exhaustion behavior, full endpoint examples, AI agent upgrade flow, and billing error codes

## Task Commits

Each task was committed atomically:

1. **Task 1: Billing routes and Stripe service layer** - `2263e46` (feat)
2. **Task 2: Verify Stripe integration with test mode** - CHECKPOINT (human-verify, approved)
3. **Task 3: Update llms.txt AI discovery files with billing documentation** - `1ee011e` (feat)

## Files Created/Modified
- `src/api/routes/billing.py` - Billing router: status, checkout, portal, PAYG toggle, webhook handler
- `src/api/services/billing.py` - Added sync_subscription_state, handle_subscription_canceled, handle_payment_failed, get_billing_status, toggle_payg, update_stripe_customer_id
- `src/api/main.py` - Registered billing router, added Billing to openapi_tags
- `static/llms.txt` - Added Billing section with credit costs, tiers, and endpoint list
- `static/llms-full.txt` - Added comprehensive Billing & Credits section (150+ lines) with tier comparison, response headers, exhaustion handling, endpoint docs, agent upgrade flow, error codes; updated Error Codes table and Rate Limiting section

## Decisions Made
- **Supabase JWT for billing endpoints:** Billing routes use get_authenticated_user (JWT auth) not API keys, since they manage account-level billing state rather than querying data.
- **Idempotent webhook handlers:** sync_subscription_state handles all subscription statuses (active -> project tier, past_due -> log warning, canceled -> downgrade). Missing records handled gracefully.
- **Payment failure logging only:** invoice.payment_failed is logged but does not immediately downgrade. Stripe has its own retry schedule and sends subscription.deleted if all retries fail.
- **Auto-create Stripe customer on PAYG enable:** Reduces friction -- users can enable PAYG without first going through checkout.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**External services require manual configuration for Stripe integration.** Environment variables needed:
- `STRIPE_SECRET_KEY` - Stripe Dashboard -> Developers -> API keys -> Secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe Dashboard -> Developers -> Webhooks -> Signing secret
- `STRIPE_PROJECT_PRICE_ID` - Stripe Dashboard -> Product catalog -> Price ID for Project plan
- `STRIPE_METER_EVENT_NAME` - Stripe Dashboard -> Billing -> Meters -> Event name (default: kalshibook_api_credits)

Note: Credit metering works locally without Stripe configured. Stripe features (checkout, portal, webhooks, PAYG) require valid keys.

## Next Phase Readiness
- Complete billing system operational: credit metering (03-01) + Stripe routes (03-02)
- All billing endpoints registered and discoverable via OpenAPI and llms.txt
- AI agents can discover full billing API via llms-full.txt including upgrade flow
- Phase 3 (Billing + Monetization) complete -- ready for Phase 4

## Self-Check: PASSED

All key files verified present. Both task commits (2263e46, 1ee011e) confirmed in git log. Checkpoint task 2 approved by user.

---
*Phase: 03-billing-monetization*
*Completed: 2026-02-14*
