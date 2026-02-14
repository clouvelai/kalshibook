# Phase 3: Billing + Monetization - Research

**Researched:** 2026-02-14
**Domain:** Credit-based API metering, Stripe Billing (Meters, Checkout, Customer Portal, Webhooks), per-key usage tracking, tiered subscriptions
**Confidence:** HIGH

## Summary

Phase 3 adds credit-based billing to the existing FastAPI API built in Phase 2. Every API request deducts credits from the user's monthly allocation. Free users get 1,000 credits/month with no card required. Users who enable PAYG get seamless overage billing at a per-credit rate via Stripe's Meter API. Project subscribers pay $30/month for 4,000 credits and higher rate limits.

The implementation has two halves: (1) local credit tracking in PostgreSQL -- a `user_credits` table with atomic decrement-on-every-request via a FastAPI dependency that hooks into the existing `get_api_key` auth flow, and (2) Stripe integration for payments -- Stripe Checkout for plan upgrades, Stripe Customer Portal for subscription management, Stripe Meter API for reporting PAYG overage usage, and webhooks for subscription lifecycle events (plan changes, cancellations, payment failures). The `stripe` Python library v14.x has native async support (`_async` suffix methods) that integrates cleanly with the project's existing async/await FastAPI + httpx pattern.

The key architectural insight is that credit tracking lives in our database (not Stripe) for low-latency enforcement on every request, while Stripe only receives aggregated PAYG overage events for billing purposes. Stripe is the payment system, not the metering system. Credits are checked and decremented locally; only overage beyond the free 1,000 credits (when PAYG is enabled) gets reported to Stripe as meter events.

**Primary recommendation:** Add a `user_credits` table for local credit tracking with atomic `UPDATE ... RETURNING` for per-request deduction. Use a new `require_credits(cost)` FastAPI dependency that chains after `get_api_key`. Report PAYG overage to Stripe Meter API asynchronously (fire-and-forget background task). Handle Stripe subscription changes via webhook endpoint at `POST /billing/webhook`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Credit Pricing Per Operation
- Different API operations cost different credit amounts based on compute complexity
- Claude's discretion on exact per-endpoint credit costs (e.g., reconstruction heavier than raw deltas, market listing cheapest)
- Reference model: Tavily charges more for advanced search vs basic -- same principle applies

#### Tier Structure
- **Free (Researcher):** 1,000 credits/month, no credit card required
- **Pay-As-You-Go:** Per-credit billing on top of free tier (PAYG toggle on dashboard, like Tavily)
- **Project:** $30/month for 4,000 credits/month
- No Enterprise tier for now -- three tiers only
- Credits reset monthly, no rollover (use it or lose it)

#### Rate Limits
- Tiered rate limits: Project tier gets higher requests/min than Free/PAYG
- Some functionality gated to Project tier only (Claude's discretion on what to gate -- e.g., reconstruction or historical depth based on compute cost and value)

#### Overage & Exhaustion Behavior
- Hard stop when credits exhausted (429 error with clear message)
- Free users without PAYG toggle: blocked until monthly reset or they enable PAYG/upgrade
- Free users with PAYG toggle: seamless overage billing at per-credit rate
- Remaining credits reported in API response headers on every request (no email notifications)

#### Stripe Integration
- Stripe Checkout (hosted page) for plan upgrades -- no embedded payment forms
- Stripe Customer Portal for subscription management (cancel, update payment method)
- Stripe Meter API for PAYG usage-based billing -- report usage to Stripe, Stripe handles invoicing
- Webhooks for subscription lifecycle events (created, updated, canceled, payment failed)

### Claude's Discretion
- Exact credit cost per endpoint
- Which features to gate behind Project tier
- Per-credit PAYG rate
- Exact rate limit numbers per tier
- Stripe product/price configuration details
- Credit tracking implementation (DB schema, deduction timing)

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope
</user_constraints>

## Discretion Recommendations

The following areas were marked as "Claude's Discretion" in CONTEXT.md. Here are researched recommendations:

### Credit Cost Per Endpoint

**Recommendation:** Assign credit costs based on compute complexity and data volume, following Tavily's model (basic=1, advanced=2).

| Endpoint | Credit Cost | Rationale |
|----------|-------------|-----------|
| `GET /markets` | 1 | Simple list query, low compute |
| `GET /markets/{ticker}` | 1 | Single row lookup with aggregation |
| `POST /deltas` | 2 | Time-range scan, pagination, medium data volume |
| `POST /orderbook` | 5 | Snapshot fetch + delta replay reconstruction, highest compute |

**Rationale:** Orderbook reconstruction is the heaviest operation (snapshot lookup + delta fetch + in-memory replay). Tavily charges 2x for "advanced" vs "basic" search. Our reconstruction is meaningfully more expensive than a simple list query, so a 5:1 ratio is justified. This gives free-tier users 1,000 market lookups OR 200 orderbook reconstructions per month -- both reasonable for a researcher evaluating the API.

### Features Gated Behind Project Tier

**Recommendation:** Gate nothing at the endpoint level. All endpoints are available to all tiers. Differentiation comes through credit allocation and rate limits only.

**Rationale:** Gating endpoints creates confusion for developers evaluating the API. A free user blocked from `/orderbook` cannot evaluate whether the product is worth paying for. Instead, the credit cost naturally gates heavy usage -- a free user gets 200 reconstructions/month (at 5 credits each), which is enough to evaluate but not enough for production use. This follows Tavily's model: all endpoints available to all tiers, differentiation through credits and rate limits.

### Per-Credit PAYG Rate

**Recommendation:** $0.008 per credit (matching Tavily exactly).

**Rationale:** Tavily charges $0.008/credit. KalshiBook's credit costs map similarly (1-5 credits per operation, so $0.008-$0.04 per request). This makes the Project tier ($30/month for 4,000 credits) a 6.25% discount vs PAYG ($32 for 4,000 credits at $0.008 each) -- a mild incentive to subscribe without making PAYG feel punitive.

### Rate Limit Numbers Per Tier

**Recommendation:**

| Tier | Requests/Minute | Rationale |
|------|-----------------|-----------|
| Free | 30 req/min | Sufficient for development/testing, not for production scraping |
| PAYG | 60 req/min | 2x free, paying customers deserve better throughput |
| Project | 120 req/min | 4x free, production-grade throughput |

**Rationale:** The existing `api_keys` table has a `rate_limit` column (default 100). Phase 2 already uses SlowAPI with key-based rate limiting. The middleware just needs to read the tier-appropriate rate limit instead of the static default. These numbers are conservative and can be increased -- it is easier to raise limits than lower them.

### Stripe Product/Price Configuration

**Recommendation:** Create the following Stripe objects:

**Products:**
1. `KalshiBook Project` -- monthly subscription product
2. `KalshiBook API Credits` -- metered usage product (for PAYG)

**Prices:**
1. Project subscription: $30/month flat recurring price
2. PAYG metered: $0.008/credit, metered usage price linked to a Stripe Meter

**Meter:**
1. `kalshibook_api_credits` -- aggregation: sum, event payload key: `value`, customer mapping: `stripe_customer_id`

**Rationale:** Two products keep the Stripe dashboard clean. The metered price only applies to PAYG users. Project users get their 4,000 credits from the subscription; if they exceed that and have PAYG enabled, overage goes through the metered price. These can be created via the Stripe Dashboard (recommended for one-time setup) rather than programmatically.

### Credit Tracking Implementation

**Recommendation:** Local PostgreSQL tracking with atomic operations. See Architecture Patterns below for full schema and patterns.

**Rationale:** Credit checks must be low-latency (sub-millisecond) since they happen on every API request. Querying Stripe on every request would add 100-300ms latency and hit rate limits. Local tracking with periodic Stripe reporting is the standard pattern for metered billing.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stripe | >=14.3.0 | Stripe API client (Checkout, Portal, Webhooks, Meters) | Official Stripe Python SDK, native async support (`_async` methods), httpx-based |
| fastapi | >=0.129.0 | Web framework (existing) | Already in project |
| asyncpg | >=0.31.0 | PostgreSQL async driver (existing) | Already in project, needed for atomic credit operations |
| pydantic | >=2.12.5 | Request/response models (existing) | Already in project |
| structlog | >=25.5.0 | Structured logging (existing) | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stripe[async] | (extra) | Installs httpx for async Stripe calls | Install instead of bare `stripe` to get async HTTP client |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local credit tracking in PostgreSQL | Stripe-only metering | Stripe Meter API adds 100-300ms latency per request; 1000 calls/s rate limit would bottleneck; local tracking is sub-ms |
| Atomic UPDATE...RETURNING | Application-level locking | DB-level atomicity is simpler and race-condition-free; no distributed lock needed |
| stripe-python async | async-stripe (third-party wrapper) | Official library now has native async since v13; third-party wrapper is unnecessary |
| Stripe Checkout (hosted) | Stripe Elements (embedded) | Checkout is simpler (no frontend), handles 3DS/SCA, PCI compliant by default. User decision locks this. |

**Installation:**
```bash
uv add "stripe[async]>=14.3.0"
```

Note: All other dependencies already in pyproject.toml from Phases 1-2.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── api/
│   ├── main.py              # Add Stripe client init to lifespan, webhook route
│   ├── deps.py              # Add require_credits() dependency
│   ├── models.py            # Add billing models (UsageInfo, BillingStatus, etc.)
│   ├── errors.py            # Add CreditsExhaustedError
│   ├── routes/
│   │   ├── billing.py       # NEW: Stripe Checkout, Portal, webhook endpoints
│   │   ├── orderbook.py     # Existing (add credit cost metadata)
│   │   ├── deltas.py        # Existing (add credit cost metadata)
│   │   ├── markets.py       # Existing (add credit cost metadata)
│   │   └── ...
│   └── services/
│       ├── billing.py       # NEW: Credit tracking, Stripe integration logic
│       ├── auth.py          # Existing
│       └── ...
├── shared/
│   └── config.py            # Add Stripe config vars
└── ...

supabase/migrations/
├── ...existing...
├── 20260215000001_create_user_credits.sql    # Credit tracking table
└── 20260215000002_create_billing_accounts.sql # Stripe customer mapping
```

### Pattern 1: User Credits Table with Atomic Decrement

**What:** A `user_credits` table tracks each user's credit balance, tier, and billing cycle. Every API request atomically decrements credits using `UPDATE ... SET credits_used = credits_used + $cost WHERE credits_remaining >= $cost RETURNING ...`. This is a single atomic SQL statement -- no race conditions, no application-level locking.

**When to use:** Every authenticated API request (via dependency injection).

**Database Schema:**
```sql
-- Billing accounts: maps Supabase users to Stripe customers and tracks tier
CREATE TABLE IF NOT EXISTS billing_accounts (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id TEXT UNIQUE,          -- null for free users without Stripe
    tier TEXT NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'payg', 'project')),
    payg_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    credits_total INT NOT NULL DEFAULT 1000, -- monthly allocation
    credits_used INT NOT NULL DEFAULT 0,     -- consumed this period
    billing_cycle_start TIMESTAMPTZ NOT NULL DEFAULT date_trunc('month', now()),
    stripe_subscription_id TEXT,             -- null for free/payg-only users
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_billing_accounts_stripe ON billing_accounts (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- Per-API-key usage tracking (for dashboard "usage by key" display)
CREATE TABLE IF NOT EXISTS api_key_usage (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    credits_charged INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Partition by month for efficient cleanup
-- (or use a rolling aggregate approach -- see notes below)
CREATE INDEX idx_api_key_usage_key_time
    ON api_key_usage (api_key_id, created_at DESC);
```

**Atomic credit deduction query:**
```sql
-- Attempt to deduct credits atomically
-- Returns the updated row if successful, empty if insufficient credits
UPDATE billing_accounts
SET credits_used = credits_used + $1,
    updated_at = now()
WHERE user_id = $2
  AND (
    -- Has remaining credits in allocation
    credits_used + $1 <= credits_total
    -- OR has PAYG enabled (unlimited with overage billing)
    OR payg_enabled = TRUE
  )
RETURNING
    user_id,
    tier,
    credits_total,
    credits_used,
    payg_enabled,
    (credits_total - credits_used) AS credits_remaining;
```

### Pattern 2: Credit Deduction via FastAPI Dependency

**What:** A `require_credits(cost: int)` dependency factory that chains after `get_api_key`. It looks up the user's billing account, atomically deducts credits, adds credit headers to the response, and raises `CreditsExhaustedError` (429) if insufficient.

**When to use:** Every data endpoint (orderbook, deltas, markets).

**Example:**
```python
# Source: Custom pattern for KalshiBook
from fastapi import Depends, Request, Response

# Credit costs per endpoint
CREDIT_COSTS = {
    "GET /markets": 1,
    "GET /markets/{ticker}": 1,
    "POST /deltas": 2,
    "POST /orderbook": 5,
}

def require_credits(cost: int):
    """Factory that returns a dependency requiring `cost` credits."""
    async def _check_credits(
        request: Request,
        key: dict = Depends(get_api_key),
        pool: asyncpg.Pool = Depends(get_db_pool),
    ) -> dict:
        # Atomic deduction
        row = await pool.fetchrow(
            """
            UPDATE billing_accounts
            SET credits_used = credits_used + $1, updated_at = now()
            WHERE user_id = $2
              AND (credits_used + $1 <= credits_total OR payg_enabled = TRUE)
            RETURNING user_id, tier, credits_total, credits_used, payg_enabled
            """,
            cost, key["user_id"],
        )
        if row is None:
            raise CreditsExhaustedError()

        credits_remaining = row["credits_total"] - row["credits_used"]

        # If PAYG and over allocation, report overage to Stripe asynchronously
        if row["payg_enabled"] and row["credits_used"] > row["credits_total"]:
            # Fire-and-forget: report to Stripe Meter API
            asyncio.create_task(report_stripe_usage(key["user_id"], cost))

        # Store credit info for response headers
        request.state.credits_remaining = max(0, credits_remaining)
        request.state.credits_used = row["credits_used"]
        request.state.credits_total = row["credits_total"]

        # Log per-key usage (fire-and-forget)
        asyncio.create_task(
            log_key_usage(pool, key["id"], request.url.path, cost)
        )

        return {**key, "tier": row["tier"]}

    return _check_credits


# Usage in endpoint
@router.post("/orderbook", response_model=OrderbookResponse)
async def get_orderbook(
    request: Request,
    body: OrderbookRequest,
    key: dict = Depends(require_credits(5)),  # 5 credits
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    ...
```

### Pattern 3: Credit Headers in Response Middleware

**What:** A middleware that injects credit usage headers into every response, following the same pattern as rate-limit headers.

**When to use:** Every API response (where credit info is available).

**Example headers:**
```
X-Credits-Remaining: 847
X-Credits-Used: 153
X-Credits-Total: 1000
X-Credits-Cost: 5
```

**Implementation:**
```python
@app.middleware("http")
async def inject_credit_headers(request: Request, call_next):
    response = await call_next(request)
    # Only add headers if credit info was set by the dependency
    if hasattr(request.state, "credits_remaining"):
        response.headers["X-Credits-Remaining"] = str(request.state.credits_remaining)
        response.headers["X-Credits-Used"] = str(request.state.credits_used)
        response.headers["X-Credits-Total"] = str(request.state.credits_total)
    return response
```

### Pattern 4: Stripe Integration (Checkout, Portal, Webhooks)

**What:** Three Stripe endpoints: (1) create a Checkout session for plan upgrades, (2) create a Portal session for subscription management, (3) receive webhook events for subscription lifecycle changes.

**When to use:** Plan upgrades, subscription management, and payment event handling.

**Stripe client initialization (lifespan):**
```python
import stripe

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # ... existing pool and supabase init ...

    # Initialize Stripe
    stripe.api_key = settings.stripe_secret_key

    yield
    # ... existing cleanup ...
```

**Checkout session (plan upgrade):**
```python
# Source: Stripe docs + FastSaaS FastAPI integration guide
@router.post("/billing/checkout")
async def create_checkout_session(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Create a Stripe Checkout session for plan upgrade."""
    # Get or create Stripe customer
    billing = await get_or_create_billing_account(pool, user["user_id"])
    customer_id = billing["stripe_customer_id"]

    if customer_id is None:
        customer = await stripe.Customer.create_async(
            email=user["email"],
            metadata={"kalshibook_user_id": user["user_id"]},
        )
        customer_id = customer.id
        await update_stripe_customer_id(pool, user["user_id"], customer_id)

    session = await stripe.checkout.Session.create_async(
        customer=customer_id,
        line_items=[{"price": settings.stripe_project_price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.app_url}/billing?success=true",
        cancel_url=f"{settings.app_url}/billing?canceled=true",
    )
    return {"checkout_url": session.url}
```

**Customer portal session:**
```python
@router.post("/billing/portal")
async def create_portal_session(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Create a Stripe Customer Portal session for subscription management."""
    billing = await get_billing_account(pool, user["user_id"])
    if not billing or not billing["stripe_customer_id"]:
        raise KalshiBookError(
            code="no_billing_account",
            message="No billing account found. Subscribe first.",
            status=400,
        )

    portal = await stripe.billing_portal.Session.create_async(
        customer=billing["stripe_customer_id"],
        return_url=f"{settings.app_url}/billing",
    )
    return {"portal_url": portal.url}
```

**Webhook handler:**
```python
# Source: Stripe docs, FastSaaS guide
@router.post("/billing/webhook")
async def stripe_webhook(request: Request, pool: asyncpg.Pool = Depends(get_db_pool)):
    """Handle Stripe webhook events for subscription lifecycle."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise KalshiBookError(code="invalid_payload", message="Invalid payload", status=400)
    except stripe.error.SignatureVerificationError:
        raise KalshiBookError(code="invalid_signature", message="Invalid signature", status=400)

    if event["type"] == "customer.subscription.created":
        await handle_subscription_created(pool, event["data"]["object"])
    elif event["type"] == "customer.subscription.updated":
        await handle_subscription_updated(pool, event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        await handle_subscription_deleted(pool, event["data"]["object"])
    elif event["type"] == "invoice.payment_failed":
        await handle_payment_failed(pool, event["data"]["object"])

    return {"status": "ok"}
```

### Pattern 5: Stripe Meter Event Reporting for PAYG Overage

**What:** When a PAYG user's credits_used exceeds credits_total, report the overage amount to Stripe's Meter API. This is done asynchronously (fire-and-forget) since billing accuracy doesn't require sub-second precision.

**When to use:** After credit deduction, only when PAYG is enabled and user is over their allocation.

**Example:**
```python
# Source: Stripe Meter Event API docs
async def report_stripe_usage(user_id: str, credits: int):
    """Report usage to Stripe Meter API for PAYG billing."""
    try:
        billing = await get_billing_account(pool, user_id)
        if not billing or not billing["stripe_customer_id"]:
            logger.warning("stripe_usage_no_customer", user_id=user_id)
            return

        await stripe.billing.MeterEvent.create_async(
            event_name="kalshibook_api_credits",
            payload={
                "stripe_customer_id": billing["stripe_customer_id"],
                "value": str(credits),
            },
        )
    except Exception:
        logger.error("stripe_usage_report_failed", user_id=user_id, credits=credits)
```

**Rate limit consideration:** Stripe Meter Events allow 1,000 calls/second in live mode. For KalshiBook's expected traffic, this is more than sufficient. If volume grows, pre-aggregate usage (e.g., batch every 60 seconds) before sending to Stripe.

### Pattern 6: Monthly Credit Reset

**What:** Credits reset at the start of each billing cycle. This can be implemented as a check-on-read pattern: when reading a user's billing account, if `billing_cycle_start` is in a previous month, reset `credits_used` to 0 and advance `billing_cycle_start`.

**When to use:** Implicitly on every credit check (lazy reset), OR via a scheduled task.

**Example (lazy reset approach):**
```sql
-- Lazy reset: atomically reset if billing cycle has rolled over
UPDATE billing_accounts
SET credits_used = 0,
    billing_cycle_start = date_trunc('month', now()),
    updated_at = now()
WHERE user_id = $1
  AND billing_cycle_start < date_trunc('month', now())
RETURNING *;
```

This is called before the credit deduction query. If it returns a row, the user's credits were reset. If it returns nothing, credits were already current. Both operations are idempotent.

### Anti-Patterns to Avoid
- **Checking Stripe on every request for credit balance:** Adds 100-300ms latency and hits Stripe's rate limits. Track credits locally, report to Stripe asynchronously.
- **Non-atomic credit deduction (read-then-write):** Race condition where two concurrent requests both read "5 credits remaining" and both deduct, resulting in negative balance. Always use `UPDATE ... WHERE credits_used + $cost <= credits_total RETURNING`.
- **Blocking on Stripe meter event reporting:** Meter events are for billing, not enforcement. Fire-and-forget with error logging. If a meter event fails, the local credit tracking still works.
- **Storing the PAYG rate in the database:** The per-credit rate is a Stripe price attribute, not application config. Stripe handles the billing math. The app just reports credit counts.
- **Complex per-key credit pools:** Credits are per-user, not per-key. A user with 3 API keys shares one credit pool. Per-key usage tracking is for display/analytics only, not enforcement.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Payment page | Custom payment form | Stripe Checkout (hosted) | PCI compliance, 3DS/SCA, Apple/Google Pay -- all handled |
| Subscription management UI | Custom cancel/update forms | Stripe Customer Portal | Payment method updates, plan changes, invoice history -- all built in |
| Usage invoicing | Custom invoice generation | Stripe Meter API + Billing | Stripe aggregates meter events, calculates amounts, generates invoices, handles failed payments |
| Webhook signature verification | Custom HMAC verification | `stripe.Webhook.construct_event()` | Handles clock skew tolerance, payload integrity, replay protection |
| Credit reset scheduling | Custom cron job | Lazy reset on read (check-on-access pattern) | No external scheduler needed, idempotent, works with any billing cycle alignment |
| Idempotent meter events | Custom deduplication | Stripe's `identifier` field on meter events | Stripe deduplicates events with same identifier within 24h+ rolling window |

**Key insight:** Stripe handles all payment complexity (PCI, SCA, invoicing, failed payment retries, proration). The application is responsible only for: (1) tracking credit consumption locally for enforcement, (2) reporting PAYG overage to Stripe for billing, and (3) responding to webhook events to update local tier/subscription state.

## Common Pitfalls

### Pitfall 1: Race Condition on Credit Deduction
**What goes wrong:** Two concurrent requests both see "5 credits remaining" and both succeed, overdrawing the account.
**Why it happens:** Read-then-write pattern without atomicity. Checking credits in one query and deducting in another.
**How to avoid:** Single atomic `UPDATE ... SET credits_used = credits_used + $cost WHERE (credits_used + $cost <= credits_total OR payg_enabled) RETURNING ...`. PostgreSQL row-level locking guarantees correctness.
**Warning signs:** credits_used exceeding credits_total for non-PAYG users.

### Pitfall 2: Webhook Event Ordering
**What goes wrong:** A `customer.subscription.deleted` event arrives before `customer.subscription.created`, causing a lookup failure.
**Why it happens:** Stripe does not guarantee event ordering. Network latency and retries can reorder events.
**How to avoid:** Make webhook handlers idempotent and handle missing records gracefully. For subscription events, use `subscription.status` as the source of truth rather than event type. An "updated" event with `status=canceled` is equivalent to a "deleted" event.
**Warning signs:** Webhook handler errors for "record not found" or "already exists."

### Pitfall 3: Webhook Signature Verification with Modified Body
**What goes wrong:** `stripe.Webhook.construct_event()` throws `SignatureVerificationError` even though the secret is correct.
**Why it happens:** FastAPI middleware or JSON parsing modifies the raw request body before verification. Stripe needs the exact raw bytes.
**How to avoid:** Use `await request.body()` to get raw bytes BEFORE any JSON parsing. Do not use Pydantic models or `request.json()` on the webhook endpoint.
**Warning signs:** All webhook events failing signature verification in one environment but not another.

### Pitfall 4: Free User Billing Account Not Provisioned
**What goes wrong:** Free user makes first API request, credit deduction fails because no `billing_accounts` row exists.
**Why it happens:** No billing account is created on signup because Phase 2 signup only creates `auth.users` and `api_keys` rows.
**How to avoid:** Create a `billing_accounts` row on first API request (upsert pattern) with `tier='free'` and `credits_total=1000`. Alternatively, trigger billing account creation from the signup flow.
**Warning signs:** 500 errors on first API request for new users.

### Pitfall 5: Meter Event Timestamp Out of Range
**What goes wrong:** Stripe rejects meter events with error about timestamp being too old.
**Why it happens:** Stripe requires meter event timestamps to be within the past 35 calendar days and no more than 5 minutes in the future.
**How to avoid:** Always send meter events promptly. If batching, ensure the batch interval stays well under 35 days (this is only a risk if the batching system has a bug that causes large backlogs). Use `datetime.now(timezone.utc)` or omit the timestamp field to let Stripe auto-set it.
**Warning signs:** Stripe API errors mentioning "timestamp" or "out of range."

### Pitfall 6: SlowAPI Rate Limits Not Tier-Aware
**What goes wrong:** All users share the same rate limit regardless of tier because the SlowAPI limiter uses a static default.
**Why it happens:** The current `_rate_limit_key` function in `main.py` returns the API key for authenticated requests, but the rate limit itself is a static `100/minute` configured on the limiter.
**How to avoid:** Use dynamic rate limits from the `billing_accounts` table. The `get_api_key` dependency already returns the key record -- extend it to include tier info, and apply tier-specific rate limits. SlowAPI supports per-route `@limiter.limit()` decorators with dynamic limit strings.
**Warning signs:** Project-tier users hitting 429s at the same threshold as free users.

## Code Examples

Verified patterns from official sources:

### Stripe Client Initialization (async)
```python
# Source: stripe-python README (https://github.com/stripe/stripe-python)
# Version: >=14.3.0 with stripe[async] extra
import stripe

# Global API key (simplest approach, used by _async methods)
stripe.api_key = settings.stripe_secret_key

# Alternative: StripeClient (explicit, recommended for new code)
client = stripe.StripeClient(
    settings.stripe_secret_key,
    http_client=stripe.HTTPXClient(),  # async-compatible
)

# Async method usage (global pattern -- simpler, matches existing codebase style)
customer = await stripe.Customer.create_async(email="user@example.com")
session = await stripe.checkout.Session.create_async(
    customer=customer.id,
    mode="subscription",
    line_items=[{"price": "price_xxx", "quantity": 1}],
    success_url="https://example.com/success",
    cancel_url="https://example.com/cancel",
)

# Meter event
await stripe.billing.MeterEvent.create_async(
    event_name="kalshibook_api_credits",
    payload={"stripe_customer_id": "cus_xxx", "value": "5"},
    identifier="unique-event-id-for-dedup",
)
```

### Stripe Webhook Handler (FastAPI)
```python
# Source: Stripe webhook docs + FastSaaS FastAPI integration guide
from fastapi import APIRouter, Request

router = APIRouter(tags=["Billing"])

@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint. No auth dependency -- uses signature verification."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid payload"})
    except stripe.error.SignatureVerificationError:
        return JSONResponse(status_code=400, content={"error": "Invalid signature"})

    event_type = event["type"]
    data = event["data"]["object"]

    match event_type:
        case "customer.subscription.created" | "customer.subscription.updated":
            # Update tier and credits based on subscription status/plan
            await sync_subscription_state(data)
        case "customer.subscription.deleted":
            # Downgrade to free tier
            await handle_subscription_canceled(data)
        case "invoice.payment_failed":
            # Log and optionally downgrade
            await handle_payment_failed(data)
        case _:
            logger.info("unhandled_webhook_event", type=event_type)

    return {"received": True}
```

### Atomic Credit Deduction (asyncpg)
```python
# Source: PostgreSQL UPDATE ... RETURNING pattern
async def deduct_credits(pool: asyncpg.Pool, user_id: str, cost: int) -> dict | None:
    """Atomically deduct credits. Returns updated account or None if insufficient.

    For PAYG users, deduction always succeeds (overage billed via Stripe).
    For non-PAYG users, deduction fails if insufficient credits.
    """
    async with pool.acquire() as conn:
        # Lazy monthly reset (idempotent)
        await conn.execute(
            """
            UPDATE billing_accounts
            SET credits_used = 0,
                billing_cycle_start = date_trunc('month', now()),
                updated_at = now()
            WHERE user_id = $1
              AND billing_cycle_start < date_trunc('month', now())
            """,
            user_id,
        )

        # Atomic deduction
        row = await conn.fetchrow(
            """
            UPDATE billing_accounts
            SET credits_used = credits_used + $1, updated_at = now()
            WHERE user_id = $2
              AND (credits_used + $1 <= credits_total OR payg_enabled = TRUE)
            RETURNING user_id, tier, credits_total, credits_used, payg_enabled
            """,
            cost, user_id,
        )

    return dict(row) if row else None
```

### Credits Exhausted Error Response
```python
# Follows existing KalshiBookError pattern from src/api/errors.py
class CreditsExhaustedError(KalshiBookError):
    """Raised when user has no remaining credits."""

    def __init__(self):
        super().__init__(
            code="credits_exhausted",
            message=(
                "Monthly credit limit reached. Enable Pay-As-You-Go for continued "
                "access or upgrade to the Project plan at /billing/checkout."
            ),
            status=429,
        )
```

### Billing Account Provisioning on First Request
```python
# Upsert pattern: create billing account if it doesn't exist
async def ensure_billing_account(pool: asyncpg.Pool, user_id: str) -> dict:
    """Get or create a billing account for a user (free tier defaults)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO billing_accounts (user_id, tier, credits_total, credits_used)
            VALUES ($1, 'free', 1000, 0)
            ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
            RETURNING *
            """,
            user_id,
        )
    return dict(row)
```

### Stripe CLI for Local Webhook Testing
```bash
# Source: Stripe CLI docs (https://docs.stripe.com/stripe-cli/use-cli)
# Forward Stripe events to local FastAPI server
stripe listen --forward-to localhost:8000/billing/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created
stripe trigger invoice.payment_failed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Legacy usage records API (`/v1/subscription_items/{id}/usage_records`) | Stripe Meter API (`/v1/billing/meter_events`) | Stripe v2025-03-31.basil | Legacy API removed. All new metered pricing must use Meters. |
| `stripe-python` sync-only | Native async with `_async` suffix methods | stripe-python v13.0.1 (2024) | No need for third-party `async-stripe` wrapper |
| Custom webhook HMAC | `stripe.Webhook.construct_event()` | Stable since 2020 | Handles clock skew, payload integrity, replay protection |
| Per-request Stripe API calls for credit checks | Local DB tracking + async Stripe reporting | Industry standard | 100-300ms savings per request, no Stripe rate limit concerns |

**Deprecated/outdated:**
- **Legacy usage records API (`create_usage_record`):** Removed in Stripe API version 2025-03-31.basil. Must use Meter API for all new usage-based billing.
- **`async-stripe` third-party package:** Unnecessary since stripe-python v13+ has native async support.
- **`stripe.api_key` without async HTTP client:** Works but uses synchronous httpx by default. Install `stripe[async]` to get the async HTTP client automatically.

## Open Questions

1. **Billing account provisioning timing**
   - What we know: Phase 2 creates `auth.users` and `api_keys` rows on signup. There is no billing account row yet.
   - What's unclear: Should the `billing_accounts` row be created during signup (in the auth proxy endpoint), or lazily on first API request?
   - Recommendation: Create lazily on first API request via upsert. This avoids modifying the existing Phase 2 signup flow and handles any users who signed up before Phase 3 was deployed. The upsert pattern is idempotent and safe for concurrent requests.

2. **PAYG toggle endpoint before dashboard exists**
   - What we know: The PAYG toggle is described as a dashboard feature (Phase 5). Phase 3 has no frontend.
   - What's unclear: How do users enable PAYG before the dashboard?
   - Recommendation: Add a `POST /billing/payg` endpoint (authenticated via Supabase JWT) that sets `payg_enabled = TRUE` on the billing account. This requires the user to have a Stripe customer with a payment method on file (verified via Stripe API). The Phase 5 dashboard will provide the UI toggle that calls this endpoint.

3. **Stripe product/price setup: Dashboard vs programmatic**
   - What we know: Products, prices, and meters need to be created in Stripe before the app can reference them.
   - What's unclear: Whether to create these via Stripe Dashboard (manual, one-time) or programmatically via migration/setup script.
   - Recommendation: Create via Stripe Dashboard. These are one-time setup actions with 2 products, 2 prices, and 1 meter. Programmatic creation adds complexity for no benefit. Store the resulting price IDs in environment variables (`STRIPE_PROJECT_PRICE_ID`, `STRIPE_PAYG_PRICE_ID`).

4. **Per-API-key usage tracking granularity**
   - What we know: Users should see credit consumption per API key (BILL-05).
   - What's unclear: How granular? Per-request log, hourly aggregates, or daily totals?
   - Recommendation: Log per-request to `api_key_usage` table (fire-and-forget INSERT). This is low-write-volume (bounded by API rate limits at ~120 req/min max). The dashboard will aggregate on read. Add a retention policy (delete usage records older than 90 days) to prevent unbounded growth.

## Sources

### Primary (HIGH confidence)
- Stripe API Reference: Meter Events (https://docs.stripe.com/api/billing/meter-event) -- meter event creation, parameters, rate limits
- Stripe API Reference: Prices (https://docs.stripe.com/api/prices/create) -- recurring, metered, billing_scheme, tiers parameters
- Stripe Checkout integration guide (https://docs.stripe.com/billing/quickstart) -- Checkout sessions, Customer Portal, webhook handling
- Stripe Usage-Based Billing implementation guide (https://docs.stripe.com/billing/subscriptions/usage-based/implementation-guide) -- meter creation, price setup, subscription flow
- Stripe Customer Portal integration (https://docs.stripe.com/customer-management/integrate-customer-portal) -- portal session creation, configuration, webhooks
- stripe-python GitHub / PyPI (https://github.com/stripe/stripe-python, https://pypi.org/project/stripe/) -- v14.3.0, async support, httpx integration
- Stripe Recording Usage API docs (https://docs.stripe.com/billing/subscriptions/usage-based/recording-usage-api) -- meter event deduplication, timestamps, rate limits
- Stripe webhook docs (https://docs.stripe.com/webhooks) -- signature verification, event ordering, retry behavior
- Stripe CLI docs (https://docs.stripe.com/stripe-cli/use-cli) -- local webhook forwarding with `stripe listen`
- FastSaaS FastAPI Stripe integration guide (https://www.fast-saas.com/blog/fastapi-stripe-integration/) -- async checkout, portal, webhook FastAPI patterns

### Secondary (MEDIUM confidence)
- Tavily pricing page (https://www.tavily.com/pricing) -- tier structure reference (Researcher/PAYG/Project)
- Tavily API credits docs (https://docs.tavily.com/documentation/api-credits) -- credit costs per operation (1 basic, 2 advanced)
- Stripe usage-based billing for AI startups (https://docs.stripe.com/get-started/use-cases/usage-based-billing) -- combined flat-fee + metered pricing architecture
- Stripe legacy usage-based billing deprecation (https://docs.stripe.com/changelog/basil/2025-03-31/deprecate-legacy-usage-based-billing) -- legacy API removed, meter API mandatory

### Tertiary (LOW confidence)
- Exact Stripe Meter Event rate limits at scale: documentation says 1,000/s for v1 API and 10,000/s for v2 meter event streams. Not verified via direct testing. Unlikely to be a concern for KalshiBook's expected traffic volume, but if scaling to thousands of concurrent users, pre-aggregation would be needed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stripe-python v14.x with async, well-documented; all other deps already in project
- Architecture: HIGH -- atomic PostgreSQL credit tracking is a proven pattern; Stripe integration follows official guides
- Pitfalls: HIGH -- race conditions, webhook ordering, signature verification are well-documented failure modes
- Discretion areas: MEDIUM -- credit costs and rate limits are reasonable starting points based on Tavily reference, but may need adjustment based on actual usage patterns post-launch

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable domain, 30-day validity)
