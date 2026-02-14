"""Billing service — credit metering, usage tracking, Stripe meter reporting.

Standalone functions (no class) following the auth.py service pattern.
Each function takes an asyncpg.Pool and operates on billing_accounts / api_key_usage tables.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
import stripe
import structlog

logger = structlog.get_logger("api.billing")


# ---------------------------------------------------------------------------
# Billing account management
# ---------------------------------------------------------------------------


async def ensure_billing_account(pool: asyncpg.Pool, user_id: str) -> dict:
    """Upsert a billing_accounts row with free-tier defaults.

    Lazily creates the account on a user's first API request.
    If the account already exists, updates `updated_at` and returns existing row.

    Returns:
        Dict with user_id, tier, credits_total, credits_used, payg_enabled,
        billing_cycle_start.
    """
    uid = UUID(user_id) if isinstance(user_id, str) else user_id

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO billing_accounts (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
            RETURNING user_id, tier, credits_total, credits_used, payg_enabled,
                      billing_cycle_start, stripe_customer_id
            """,
            uid,
        )

    logger.debug("billing_account_ensured", user_id=user_id, tier=row["tier"])

    return dict(row)


# ---------------------------------------------------------------------------
# Monthly credit reset
# ---------------------------------------------------------------------------


async def lazy_reset_credits(pool: asyncpg.Pool, user_id: str) -> None:
    """Reset credits if the billing cycle has rolled into a new month.

    Atomically sets credits_used to 0 and advances billing_cycle_start
    to the first day of the current month. Idempotent — safe to call
    on every request.
    """
    uid = UUID(user_id) if isinstance(user_id, str) else user_id

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE billing_accounts
            SET credits_used = 0,
                billing_cycle_start = date_trunc('month', now()),
                updated_at = now()
            WHERE user_id = $1
              AND billing_cycle_start < date_trunc('month', now())
            """,
            uid,
        )

    if result == "UPDATE 1":
        logger.info("billing_credits_reset", user_id=user_id)


# ---------------------------------------------------------------------------
# Credit deduction
# ---------------------------------------------------------------------------


async def deduct_credits(pool: asyncpg.Pool, user_id: str, cost: int) -> dict | None:
    """Atomically deduct credits from a user's billing account.

    First resets credits if needed (new month), then attempts an atomic
    deduction. Allows overdraft only if payg_enabled is TRUE.

    Returns:
        Dict with user_id, tier, credits_total, credits_used, payg_enabled
        if deduction succeeded. None if insufficient credits and not PAYG.
    """
    # Reset credits if billing cycle rolled over
    await lazy_reset_credits(pool, user_id)

    uid = UUID(user_id) if isinstance(user_id, str) else user_id

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE billing_accounts
            SET credits_used = credits_used + $2,
                updated_at = now()
            WHERE user_id = $1
              AND (credits_used + $2 <= credits_total OR payg_enabled = TRUE)
            RETURNING user_id, tier, credits_total, credits_used, payg_enabled
            """,
            uid,
            cost,
        )

    if row is None:
        logger.warning("credits_exhausted", user_id=user_id, cost=cost)
        return None

    logger.debug(
        "credits_deducted",
        user_id=user_id,
        cost=cost,
        credits_used=row["credits_used"],
        credits_total=row["credits_total"],
    )

    return dict(row)


# ---------------------------------------------------------------------------
# Per-key usage logging
# ---------------------------------------------------------------------------


async def log_key_usage(
    pool: asyncpg.Pool, api_key_id: str, endpoint: str, credits_charged: int
) -> None:
    """Insert a usage record for the given API key.

    Fire-and-forget: exceptions are logged but not raised to avoid
    disrupting the request flow.
    """
    try:
        key_uuid = UUID(api_key_id) if isinstance(api_key_id, str) else api_key_id

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_key_usage (api_key_id, endpoint, credits_charged)
                VALUES ($1, $2, $3)
                """,
                key_uuid,
                endpoint,
                credits_charged,
            )
    except Exception:
        logger.error(
            "usage_log_failed",
            api_key_id=api_key_id,
            endpoint=endpoint,
            credits_charged=credits_charged,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Stripe meter event reporting
# ---------------------------------------------------------------------------


async def report_stripe_usage(
    stripe_customer_id: str, credits: int, event_name: str
) -> None:
    """Report PAYG overage credits to Stripe Billing Meter API.

    Fire-and-forget: exceptions are logged but not raised.
    Only called when payg_enabled AND credits_used > credits_total.
    """
    try:
        await stripe.billing.MeterEvent.create_async(
            event_name=event_name,
            payload={
                "stripe_customer_id": stripe_customer_id,
                "value": str(credits),
            },
        )
        logger.info(
            "stripe_usage_reported",
            stripe_customer_id=stripe_customer_id,
            credits=credits,
            event_name=event_name,
        )
    except Exception:
        logger.error(
            "stripe_usage_report_failed",
            stripe_customer_id=stripe_customer_id,
            credits=credits,
            event_name=event_name,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Billing status query
# ---------------------------------------------------------------------------


async def get_billing_status(pool: asyncpg.Pool, user_id: str) -> dict | None:
    """Fetch the billing account for a user.

    Returns:
        Dict with billing account fields, or None if no account exists.
    """
    uid = UUID(user_id) if isinstance(user_id, str) else user_id

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, tier, credits_total, credits_used, payg_enabled,
                   billing_cycle_start, stripe_customer_id, stripe_subscription_id
            FROM billing_accounts
            WHERE user_id = $1
            """,
            uid,
        )

    if row is None:
        return None

    return dict(row)


# ---------------------------------------------------------------------------
# Stripe customer ID management
# ---------------------------------------------------------------------------


async def update_stripe_customer_id(
    pool: asyncpg.Pool, user_id: str, stripe_customer_id: str
) -> None:
    """Store the Stripe customer ID on a billing account."""
    uid = UUID(user_id) if isinstance(user_id, str) else user_id

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE billing_accounts
            SET stripe_customer_id = $2, updated_at = now()
            WHERE user_id = $1
            """,
            uid,
            stripe_customer_id,
        )

    logger.info("stripe_customer_id_updated", user_id=user_id, stripe_customer_id=stripe_customer_id)


# ---------------------------------------------------------------------------
# PAYG toggle
# ---------------------------------------------------------------------------


async def toggle_payg(pool: asyncpg.Pool, user_id: str, enable: bool) -> dict:
    """Enable or disable Pay-As-You-Go billing.

    When enabling: sets payg_enabled=TRUE.  If currently 'free' tier, upgrades to 'payg'.
    When disabling: sets payg_enabled=FALSE. If no active subscription, reverts to 'free'.

    Returns:
        Updated billing account dict.
    """
    uid = UUID(user_id) if isinstance(user_id, str) else user_id

    async with pool.acquire() as conn:
        if enable:
            row = await conn.fetchrow(
                """
                UPDATE billing_accounts
                SET payg_enabled = TRUE,
                    tier = CASE WHEN tier = 'free' THEN 'payg' ELSE tier END,
                    updated_at = now()
                WHERE user_id = $1
                RETURNING user_id, tier, credits_total, credits_used, payg_enabled,
                          billing_cycle_start, stripe_customer_id, stripe_subscription_id
                """,
                uid,
            )
        else:
            row = await conn.fetchrow(
                """
                UPDATE billing_accounts
                SET payg_enabled = FALSE,
                    tier = CASE
                        WHEN stripe_subscription_id IS NULL THEN 'free'
                        ELSE tier
                    END,
                    updated_at = now()
                WHERE user_id = $1
                RETURNING user_id, tier, credits_total, credits_used, payg_enabled,
                          billing_cycle_start, stripe_customer_id, stripe_subscription_id
                """,
                uid,
            )

    logger.info("payg_toggled", user_id=user_id, enable=enable, tier=row["tier"])
    return dict(row)


# ---------------------------------------------------------------------------
# Stripe webhook handlers
# ---------------------------------------------------------------------------


async def sync_subscription_state(pool: asyncpg.Pool, subscription_data: dict) -> None:
    """Process a subscription.created or subscription.updated webhook event.

    Extracts customer ID from the subscription object, looks up the billing
    account, and updates tier/credits based on subscription status.  Idempotent.

    Subscription status mapping:
        - 'active'   -> tier='project', credits_total=4000
        - 'past_due' -> keep project tier (Stripe retries payment)
        - 'canceled' / 'unpaid' -> downgrade to free
    """
    customer_id = subscription_data.get("customer")
    subscription_id = subscription_data.get("id")
    status = subscription_data.get("status", "")

    if not customer_id:
        logger.warning("sync_subscription_missing_customer", data=subscription_data)
        return

    async with pool.acquire() as conn:
        account = await conn.fetchrow(
            "SELECT user_id FROM billing_accounts WHERE stripe_customer_id = $1",
            customer_id,
        )

        if account is None:
            logger.warning(
                "sync_subscription_no_account",
                stripe_customer_id=customer_id,
                subscription_id=subscription_id,
            )
            return

        if status in ("active", "trialing"):
            await conn.execute(
                """
                UPDATE billing_accounts
                SET tier = 'project',
                    credits_total = 4000,
                    stripe_subscription_id = $2,
                    updated_at = now()
                WHERE user_id = $1
                """,
                account["user_id"],
                subscription_id,
            )
            logger.info(
                "subscription_synced_project",
                user_id=str(account["user_id"]),
                subscription_id=subscription_id,
                status=status,
            )
        elif status == "past_due":
            # Keep project tier — Stripe will retry payment
            await conn.execute(
                """
                UPDATE billing_accounts
                SET stripe_subscription_id = $2,
                    updated_at = now()
                WHERE user_id = $1
                """,
                account["user_id"],
                subscription_id,
            )
            logger.warning(
                "subscription_past_due",
                user_id=str(account["user_id"]),
                subscription_id=subscription_id,
            )
        elif status in ("canceled", "unpaid"):
            await conn.execute(
                """
                UPDATE billing_accounts
                SET tier = 'free',
                    credits_total = 1000,
                    stripe_subscription_id = NULL,
                    payg_enabled = FALSE,
                    updated_at = now()
                WHERE user_id = $1
                """,
                account["user_id"],
            )
            logger.info(
                "subscription_downgraded",
                user_id=str(account["user_id"]),
                subscription_id=subscription_id,
                status=status,
            )
        else:
            logger.info(
                "subscription_status_unhandled",
                user_id=str(account["user_id"]),
                subscription_id=subscription_id,
                status=status,
            )


async def handle_subscription_canceled(pool: asyncpg.Pool, subscription_data: dict) -> None:
    """Process a subscription.deleted webhook event.

    Downgrades the billing account to free tier.  Idempotent — handles
    missing records gracefully.
    """
    customer_id = subscription_data.get("customer")

    if not customer_id:
        logger.warning("cancel_missing_customer", data=subscription_data)
        return

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE billing_accounts
            SET tier = 'free',
                credits_total = 1000,
                stripe_subscription_id = NULL,
                payg_enabled = FALSE,
                updated_at = now()
            WHERE stripe_customer_id = $1
            """,
            customer_id,
        )

    if result == "UPDATE 0":
        logger.warning("cancel_no_account_found", stripe_customer_id=customer_id)
    else:
        logger.info("subscription_canceled", stripe_customer_id=customer_id)


async def handle_payment_failed(pool: asyncpg.Pool, invoice_data: dict) -> None:
    """Process an invoice.payment_failed webhook event.

    Logs the failure but does NOT immediately downgrade the account.
    Stripe has its own retry schedule and will eventually send
    customer.subscription.deleted if all retries fail.
    """
    customer_id = invoice_data.get("customer")
    invoice_id = invoice_data.get("id")
    attempt_count = invoice_data.get("attempt_count", 0)

    logger.warning(
        "payment_failed",
        stripe_customer_id=customer_id,
        invoice_id=invoice_id,
        attempt_count=attempt_count,
    )

    if customer_id:
        async with pool.acquire() as conn:
            account = await conn.fetchrow(
                "SELECT user_id, tier FROM billing_accounts WHERE stripe_customer_id = $1",
                customer_id,
            )
            if account:
                logger.warning(
                    "payment_failed_account",
                    user_id=str(account["user_id"]),
                    tier=account["tier"],
                    stripe_customer_id=customer_id,
                    invoice_id=invoice_id,
                    attempt_count=attempt_count,
                )
