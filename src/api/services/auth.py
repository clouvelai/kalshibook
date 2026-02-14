"""API key generation, hashing, and database operations.

Keys use the format: kb-{random_bytes}
Only the SHA-256 hash is stored in the database. The raw key is shown once at creation.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

import asyncpg
import structlog

logger = structlog.get_logger("api.auth")


# ---------------------------------------------------------------------------
# Key generation and hashing
# ---------------------------------------------------------------------------

def generate_api_key() -> tuple[str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (raw_key, sha256_hash).
        The raw key starts with 'kb-' and uses URL-safe base64 encoding.
    """
    raw_key = "kb-" + secrets.token_urlsafe(32)
    key_hash = hash_api_key(raw_key)
    return raw_key, key_hash


def hash_api_key(raw_key: str) -> str:
    """Compute the SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

async def create_api_key(
    pool: asyncpg.Pool,
    user_id: str,
    name: str = "Default",
) -> dict:
    """Create a new API key for a user.

    Returns a dict with id, key (raw), name, key_prefix, created_at.
    The raw key is included so it can be shown to the user once.
    """
    raw_key, key_hash = generate_api_key()
    key_prefix = raw_key[:7]  # "kb-abcd" — enough for display

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (user_id, key_hash, key_prefix, name)
            VALUES ($1, $2, $3, $4)
            RETURNING id, created_at
            """,
            user_id,
            key_hash,
            key_prefix,
            name,
        )

    logger.info("api_key_created", user_id=user_id, key_prefix=key_prefix, name=name)

    return {
        "id": str(row["id"]),
        "key": raw_key,
        "name": name,
        "key_prefix": key_prefix,
        "created_at": row["created_at"].isoformat(),
    }


async def validate_api_key(pool: asyncpg.Pool, raw_key: str) -> dict | None:
    """Validate an API key by hashing and looking it up.

    Uses constant-time comparison via hmac.compare_digest to prevent timing attacks.

    Returns:
        Key record dict (id, user_id, name, rate_limit) if valid, None otherwise.
    """
    key_hash = hash_api_key(raw_key)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, name, rate_limit, key_hash
            FROM api_keys
            WHERE key_hash = $1 AND revoked_at IS NULL
            """,
            key_hash,
        )

    if row is None:
        return None

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(row["key_hash"], key_hash):
        return None

    # Update last_used_at asynchronously (fire-and-forget for performance)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET last_used_at = $1 WHERE id = $2",
            datetime.now(timezone.utc),
            row["id"],
        )

    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "name": row["name"],
        "rate_limit": row["rate_limit"],
    }


async def list_api_keys(pool: asyncpg.Pool, user_id: str) -> list[dict]:
    """List all non-revoked API keys for a user.

    Returns a list of dicts with id, name, key_prefix, created_at, last_used_at.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, key_prefix, created_at, last_used_at
            FROM api_keys
            WHERE user_id = $1 AND revoked_at IS NULL
            ORDER BY created_at DESC
            """,
            user_id,
        )

    return [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "key_prefix": row["key_prefix"],
            "created_at": row["created_at"].isoformat(),
            "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
        }
        for row in rows
    ]


async def revoke_api_key(pool: asyncpg.Pool, key_id: str, user_id: str) -> bool:
    """Revoke an API key by setting revoked_at.

    Returns True if the key was found and revoked, False otherwise.
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE api_keys
            SET revoked_at = now()
            WHERE id = $1 AND user_id = $2 AND revoked_at IS NULL
            """,
            key_id,
            user_id,
        )

    revoked = result == "UPDATE 1"
    if revoked:
        logger.info("api_key_revoked", key_id=key_id, user_id=user_id)
    else:
        logger.warning("api_key_revoke_failed", key_id=key_id, user_id=user_id)
    return revoked
