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
    result = await create_api_key(pool, user["user_id"], body.name)

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
