"""Database connection pool management using asyncpg."""

from __future__ import annotations

import asyncpg
import structlog

logger = structlog.get_logger("db")

# Module-level pool singleton
_pool: asyncpg.Pool | None = None


async def create_pool(
    dsn: str,
    min_size: int = 5,
    max_size: int = 20,
) -> asyncpg.Pool:
    """Create and return an asyncpg connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=min_size,
        max_size=max_size,
    )
    logger.info("db_pool_created", min_size=min_size, max_size=max_size)
    return _pool


def get_pool() -> asyncpg.Pool:
    """Get the existing connection pool. Raises if not created."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call create_pool() first.")
    return _pool


async def close_pool() -> None:
    """Close the connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("db_pool_closed")


async def ensure_partitions(pool: asyncpg.Pool, days_ahead: int = 7, months_ahead: int = 3) -> None:
    """Create future partitions for deltas and snapshots tables."""
    async with pool.acquire() as conn:
        await conn.execute(
            "SELECT create_future_partitions($1, $2)",
            days_ahead,
            months_ahead,
        )
    logger.info("partitions_ensured", days_ahead=days_ahead, months_ahead=months_ahead)
