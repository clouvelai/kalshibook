"""FastAPI dependency injection for authentication and database access."""

from __future__ import annotations

import asyncio
from uuid import UUID

import asyncpg
from fastapi import Depends, Request

from src.api.errors import CreditsExhaustedError, InvalidApiKeyError, KalshiBookError
from src.api.services.auth import validate_api_key
from src.api.services.billing import (
    deduct_credits,
    ensure_billing_account,
    log_key_usage,
    report_stripe_usage,
)
from src.shared.config import get_settings

# ---------------------------------------------------------------------------
# Database pool dependency
# ---------------------------------------------------------------------------

async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Return the asyncpg connection pool from app state."""
    return request.app.state.pool


# ---------------------------------------------------------------------------
# API key authentication dependency
# ---------------------------------------------------------------------------

async def get_api_key(
    request: Request,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """Extract and validate the API key from the Authorization header.

    Expected format: Authorization: Bearer kb-...

    Returns:
        Key record dict with id, user_id, name, rate_limit.

    Raises:
        InvalidApiKeyError: If the key is missing, malformed, or invalid.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise InvalidApiKeyError(
            "Missing or malformed Authorization header. Expected: Bearer kb-..."
        )

    raw_key = auth_header.removeprefix("Bearer ").strip()

    if not raw_key.startswith("kb-"):
        raise InvalidApiKeyError("Invalid API key format. Keys must start with 'kb-'.")

    key_record = await validate_api_key(pool, raw_key)

    if key_record is None:
        raise InvalidApiKeyError()

    return key_record


# ---------------------------------------------------------------------------
# Credit metering constants
# ---------------------------------------------------------------------------

CREDIT_COSTS = {
    "markets": 1,
    "market_detail": 1,
    "deltas": 2,
    "orderbook": 5,
}

TIER_RATE_LIMITS = {
    "free": "30/minute",
    "payg": "60/minute",
    "project": "120/minute",
}


# ---------------------------------------------------------------------------
# Credit deduction dependency factory
# ---------------------------------------------------------------------------

def require_credits(cost: int):
    """Factory returning a dependency that deducts `cost` credits.

    Chains after get_api_key, ensuring authentication before credit check.
    Stores credit info on request.state for the response headers middleware.
    """

    async def _check_credits(
        request: Request,
        key: dict = Depends(get_api_key),
        pool: asyncpg.Pool = Depends(get_db_pool),
    ) -> dict:
        user_id = key["user_id"]

        # Ensure billing account exists (lazy upsert on first request)
        await ensure_billing_account(pool, user_id)

        # Atomic credit deduction
        row = await deduct_credits(pool, user_id, cost)
        if row is None:
            raise CreditsExhaustedError()

        credits_remaining = max(0, row["credits_total"] - row["credits_used"])

        # Store credit info on request.state for response headers
        request.state.credits_remaining = credits_remaining
        request.state.credits_used = row["credits_used"]
        request.state.credits_total = row["credits_total"]
        request.state.credits_cost = cost
        request.state.tier = row["tier"]

        # If PAYG and over allocation, report overage to Stripe (fire-and-forget)
        if row["payg_enabled"] and row["credits_used"] > row["credits_total"]:
            billing = await pool.fetchrow(
                "SELECT stripe_customer_id FROM billing_accounts WHERE user_id = $1",
                UUID(key["user_id"]) if isinstance(key["user_id"], str) else key["user_id"],
            )
            if billing and billing["stripe_customer_id"]:
                settings = get_settings()
                asyncio.create_task(
                    report_stripe_usage(
                        billing["stripe_customer_id"],
                        cost,
                        settings.stripe_meter_event_name,
                    )
                )

        # Log per-key usage (fire-and-forget)
        asyncio.create_task(log_key_usage(pool, key["id"], request.url.path, cost))

        return {**key, "tier": row["tier"]}

    return _check_credits


# ---------------------------------------------------------------------------
# Supabase JWT authentication dependency (for key management endpoints)
# ---------------------------------------------------------------------------

async def get_authenticated_user(request: Request) -> dict:
    """Validate a Supabase JWT and return user info.

    Used by key management endpoints (/keys) which require a Supabase
    access token (from POST /auth/login), NOT an API key.

    Returns:
        Dict with user_id and email.

    Raises:
        InvalidApiKeyError: If the token is missing or invalid.
        KalshiBookError: If an API key is used instead of a JWT.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise InvalidApiKeyError("Missing Bearer token")

    token = auth_header.removeprefix("Bearer ").strip()

    # Supabase JWT tokens don't start with "kb-"
    if token.startswith("kb-"):
        raise KalshiBookError(
            code="invalid_auth_method",
            message=(
                "Key management endpoints require a Supabase access token, "
                "not an API key. Use POST /auth/login to get an access token."
            ),
            status=401,
        )

    # Validate JWT via Supabase Auth
    supabase = request.app.state.supabase
    user = await supabase.get_user(token)

    if user is None:
        raise InvalidApiKeyError("Invalid or expired access token")

    return {"user_id": user["user_id"], "email": user["email"]}


# ---------------------------------------------------------------------------
# Supabase client dependency (for auth operations)
# ---------------------------------------------------------------------------

async def get_supabase_client(request: Request):
    """Return the Supabase auth client from app state.

    The Supabase client is initialized in the app lifespan.
    Returns None if not yet configured.
    """
    return getattr(request.app.state, "supabase", None)
