"""FastAPI dependency injection for authentication and database access."""

from __future__ import annotations

import asyncpg
from fastapi import Depends, Request

from src.api.errors import InvalidApiKeyError, KalshiBookError
from src.api.services.auth import validate_api_key

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
