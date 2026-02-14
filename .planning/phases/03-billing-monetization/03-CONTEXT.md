# Phase 3: Billing + Monetization - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Credit-based API metering with three tiers (Free, Pay-As-You-Go, Project), Stripe-managed subscriptions and usage billing, and per-API-key usage tracking. Users can use the API for free up to 1,000 credits/month, enable PAYG for overage billing, or subscribe to Project tier for bundled credits and higher limits.

</domain>

<decisions>
## Implementation Decisions

### Credit Pricing Per Operation
- Different API operations cost different credit amounts based on compute complexity
- Claude's discretion on exact per-endpoint credit costs (e.g., reconstruction heavier than raw deltas, market listing cheapest)
- Reference model: Tavily charges more for advanced search vs basic — same principle applies

### Tier Structure
- **Free (Researcher):** 1,000 credits/month, no credit card required
- **Pay-As-You-Go:** Per-credit billing on top of free tier (PAYG toggle on dashboard, like Tavily)
- **Project:** $30/month for 4,000 credits/month
- No Enterprise tier for now — three tiers only
- Credits reset monthly, no rollover (use it or lose it)

### Rate Limits
- Tiered rate limits: Project tier gets higher requests/min than Free/PAYG
- Some functionality gated to Project tier only (Claude's discretion on what to gate — e.g., reconstruction or historical depth based on compute cost and value)

### Overage & Exhaustion Behavior
- Hard stop when credits exhausted (429 error with clear message)
- Free users without PAYG toggle: blocked until monthly reset or they enable PAYG/upgrade
- Free users with PAYG toggle: seamless overage billing at per-credit rate
- Remaining credits reported in API response headers on every request (no email notifications)

### Stripe Integration
- Stripe Checkout (hosted page) for plan upgrades — no embedded payment forms
- Stripe Customer Portal for subscription management (cancel, update payment method)
- Stripe Meter API for PAYG usage-based billing — report usage to Stripe, Stripe handles invoicing
- Webhooks for subscription lifecycle events (created, updated, canceled, payment failed)

### Claude's Discretion
- Exact credit cost per endpoint
- Which features to gate behind Project tier
- Per-credit PAYG rate
- Exact rate limit numbers per tier
- Stripe product/price configuration details
- Credit tracking implementation (DB schema, deduction timing)

</decisions>

<specifics>
## Specific Ideas

- "Follow the Tavily model" — free with limit, pay as you go, monthly. Simple, clean, easy to understand.
- Tavily dashboard reference: shows current plan name, credit usage bar (0/1,000), PAYG toggle, and API keys table on one clean overview page
- PAYG toggle sits right below the credit usage display — users can flip it on without navigating away

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-billing-monetization*
*Context gathered: 2026-02-14*
