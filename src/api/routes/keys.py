"""API key management endpoints — POST /keys, GET /keys, DELETE /keys/{id}.

All key management endpoints require Supabase JWT authentication
(not API key auth). Users must first login via POST /auth/login to
get an access token, then use that token to manage their API keys.
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.api.deps import get_authenticated_user, get_db_pool
from src.api.errors import KalshiBookError
from src.api.models import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeysResponse,
    KeysUsageResponse,
)
from src.api.services.auth import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(tags=["API Keys"])


@router.post("/keys", response_model=ApiKeyCreatedResponse)
async def create_key(
    body: ApiKeyCreate,
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Create a new API key.

    Requires a Supabase access token (from POST /auth/login).
    The raw API key is returned once in the response — store it securely.
    """
    request_id = getattr(request.state, "request_id", "")
    result = await create_api_key(pool, user["user_id"], body.name, body.key_type)

    return ApiKeyCreatedResponse(
        data=result,
        request_id=request_id,
    )


@router.get("/keys", response_model=ApiKeysResponse)
async def list_keys(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """List all active API keys for the authenticated user.

    Requires a Supabase access token (from POST /auth/login).
    Returns key prefixes only — raw keys are never shown after creation.
    """
    request_id = getattr(request.state, "request_id", "")
    keys = await list_api_keys(pool, user["user_id"])

    return ApiKeysResponse(
        data=keys,
        request_id=request_id,
    )


@router.get("/keys/usage", response_model=KeysUsageResponse)
async def get_keys_usage(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get per-key credit usage for the current billing cycle.

    Requires a Supabase access token (from POST /auth/login).
    Aggregates credits_charged from api_key_usage, scoped to the
    current billing cycle start from the user's billing account.
    """
    request_id = getattr(request.state, "request_id", "")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                ak.id,
                ak.name,
                ak.key_prefix,
                ak.key_type,
                ak.created_at,
                ak.last_used_at,
                COALESCE(SUM(aku.credits_charged), 0)::bigint AS credits_used
            FROM api_keys ak
            LEFT JOIN api_key_usage aku
                ON aku.api_key_id = ak.id
                AND aku.created_at >= (
                    SELECT COALESCE(ba.billing_cycle_start, date_trunc('month', now()))
                    FROM billing_accounts ba
                    WHERE ba.user_id = ak.user_id
                )
            WHERE ak.user_id = $1
              AND ak.revoked_at IS NULL
            GROUP BY ak.id, ak.name, ak.key_prefix, ak.key_type, ak.created_at, ak.last_used_at
            ORDER BY ak.created_at DESC
            """,
            user["user_id"],
        )

    data = [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "key_prefix": row["key_prefix"],
            "key_type": row["key_type"],
            "created_at": row["created_at"].isoformat(),
            "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
            "credits_used": row["credits_used"],
        }
        for row in rows
    ]

    return KeysUsageResponse(data=data, request_id=request_id)


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: str,
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Revoke an API key.

    Requires a Supabase access token (from POST /auth/login).
    The key must belong to the authenticated user.
    """
    request_id = getattr(request.state, "request_id", "")
    revoked = await revoke_api_key(pool, key_id, user["user_id"])

    if not revoked:
        raise KalshiBookError(
            code="key_not_found",
            message="API key not found or already revoked.",
            status=404,
        )

    return {"message": "API key revoked", "request_id": request_id}
