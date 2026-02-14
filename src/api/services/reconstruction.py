"""Orderbook reconstruction: snapshot + delta replay.

Given a market ticker and target timestamp, reconstructs the orderbook state by:
1. Finding the most recent snapshot before the target time
2. Fetching all deltas between that snapshot and the target time
3. Applying deltas to the snapshot levels in sequence order
"""

from __future__ import annotations

from datetime import datetime

import asyncpg
import structlog

logger = structlog.get_logger("api.reconstruction")


async def get_earliest_snapshot_time(
    pool: asyncpg.Pool, market_ticker: str
) -> datetime | None:
    """Find the earliest snapshot timestamp for a market.

    Used for error messages when the requested timestamp predates available data.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT captured_at
            FROM snapshots
            WHERE market_ticker = $1
            ORDER BY captured_at ASC
            LIMIT 1
            """,
            market_ticker,
        )
    return row["captured_at"] if row else None


async def reconstruct_orderbook(
    pool: asyncpg.Pool,
    market_ticker: str,
    at_timestamp: datetime,
    depth: int | None = None,
) -> dict | None:
    """Reconstruct the orderbook state at a specific timestamp.

    Algorithm:
        1. Find the most recent snapshot before at_timestamp
        2. If no snapshot, check if the market has ANY data (for error messages)
        3. Fetch deltas between snapshot and target timestamp
        4. Apply deltas to snapshot levels
        5. Sort and optionally truncate by depth

    Returns:
        - dict with reconstructed orderbook on success
        - dict with {"error": "no_data", "earliest_available_at": ...} if timestamp
          is before first snapshot but market has data
        - None if market has no data at all
    """
    async with pool.acquire() as conn:
        # Step 1: Most recent snapshot before target timestamp
        snapshot = await conn.fetchrow(
            """
            SELECT captured_at, seq, yes_levels, no_levels
            FROM snapshots
            WHERE market_ticker = $1 AND captured_at <= $2
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            market_ticker,
            at_timestamp,
        )

        if snapshot is None:
            # Step 2: No snapshot before target -- check if market has ANY data
            earliest = await conn.fetchrow(
                """
                SELECT captured_at
                FROM snapshots
                WHERE market_ticker = $1
                ORDER BY captured_at ASC
                LIMIT 1
                """,
                market_ticker,
            )
            if earliest is not None:
                return {
                    "error": "no_data",
                    "earliest_available_at": earliest["captured_at"].isoformat(),
                }
            # No snapshots at all for this market
            return None

        # Step 3: Fetch all deltas between snapshot and target timestamp
        deltas = await conn.fetch(
            """
            SELECT price_cents, delta_amount, side, seq
            FROM deltas
            WHERE market_ticker = $1 AND ts > $2 AND ts <= $3
            ORDER BY seq ASC
            """,
            market_ticker,
            snapshot["captured_at"],
            at_timestamp,
        )

    # Step 4: Apply deltas to snapshot levels
    # yes_levels and no_levels are JSONB arrays of [price_cents, quantity] pairs
    # asyncpg deserializes JSONB to Python lists automatically
    yes_book: dict[int, int] = {
        int(level[0]): int(level[1]) for level in (snapshot["yes_levels"] or [])
    }
    no_book: dict[int, int] = {
        int(level[0]): int(level[1]) for level in (snapshot["no_levels"] or [])
    }

    for delta in deltas:
        book = yes_book if delta["side"] == "yes" else no_book
        price = delta["price_cents"]
        book[price] = book.get(price, 0) + delta["delta_amount"]
        if book[price] <= 0:
            book.pop(price, None)

    # Step 5: Sort levels by price descending, optionally limit depth
    yes_levels = sorted(
        [{"price": p, "quantity": q} for p, q in yes_book.items()],
        key=lambda x: x["price"],
        reverse=True,
    )
    no_levels = sorted(
        [{"price": p, "quantity": q} for p, q in no_book.items()],
        key=lambda x: x["price"],
        reverse=True,
    )

    if depth is not None:
        yes_levels = yes_levels[:depth]
        no_levels = no_levels[:depth]

    logger.debug(
        "orderbook_reconstructed",
        market_ticker=market_ticker,
        at_timestamp=at_timestamp.isoformat(),
        snapshot_basis=snapshot["captured_at"].isoformat(),
        deltas_applied=len(deltas),
        yes_levels=len(yes_levels),
        no_levels=len(no_levels),
    )

    return {
        "market_ticker": market_ticker,
        "timestamp": at_timestamp.isoformat(),
        "snapshot_basis": snapshot["captured_at"].isoformat(),
        "deltas_applied": len(deltas),
        "yes": yes_levels,
        "no": no_levels,
    }
