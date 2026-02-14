"""FastAPI dependency injection for authentication and database access."""

from __future__ import annotations

import asyncpg
from fastapi import Depends, Request

from src.api.errors import InvalidApiKeyError
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
# Supabase client dependency (for auth operations)
# ---------------------------------------------------------------------------

async def get_supabase_client(request: Request):
    """Return the Supabase admin client from app state.

    The Supabase client is initialized in the app lifespan (Plan 02-03).
    Returns None if not yet configured.
    """
    return getattr(request.app.state, "supabase", None)
