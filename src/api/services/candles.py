"""Candlestick computation service -- SQL-based OHLCV aggregation from raw trade data.

Computes open/high/low/close/volume candles at minute, hour, and day intervals
using Postgres date_trunc aggregation on the trades table.
"""

from __future__ import annotations

import asyncpg

from src.api.errors import ValidationError

# ---------------------------------------------------------------------------
# Valid intervals: user-facing string -> Postgres date_trunc argument
# ---------------------------------------------------------------------------

VALID_INTERVALS = {"1m": "minute", "1h": "hour", "1d": "day"}

# ---------------------------------------------------------------------------
# Candle aggregation query
# ---------------------------------------------------------------------------

CANDLE_QUERY = """
SELECT
    date_trunc($4, ts AT TIME ZONE 'UTC') AS bucket,
    market_ticker,
    (array_agg(yes_price ORDER BY ts ASC))[1] AS open,
    MAX(yes_price) AS high,
    MIN(yes_price) AS low,
    (array_agg(yes_price ORDER BY ts DESC))[1] AS close,
    SUM(count) AS volume,
    COUNT(*) AS trade_count
FROM trades
WHERE market_ticker = $1
  AND ts >= $2
  AND ts < $3
GROUP BY bucket, market_ticker
ORDER BY bucket ASC
"""


# ---------------------------------------------------------------------------
# Service function
# ---------------------------------------------------------------------------

async def get_candles(
    pool: asyncpg.Pool,
    market_ticker: str,
    start_time,
    end_time,
    interval: str,
) -> list[dict]:
    """Compute OHLCV candles for a market over a time range.

    Args:
        pool: asyncpg connection pool.
        market_ticker: Kalshi market ticker.
        start_time: Start of time range (inclusive).
        end_time: End of time range (exclusive).
        interval: Postgres date_trunc interval ('minute', 'hour', or 'day').

    Returns:
        List of dicts with keys: bucket, market_ticker, open, high, low, close,
        volume, trade_count. Empty list if no trades in range.

    Raises:
        ValidationError: If interval is not one of the valid values.
    """
    valid_pg_intervals = set(VALID_INTERVALS.values())
    if interval not in valid_pg_intervals:
        raise ValidationError(
            f"Invalid interval '{interval}'. Must be one of: {', '.join(sorted(valid_pg_intervals))}"
        )

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            CANDLE_QUERY,
            market_ticker,
            start_time,
            end_time,
            interval,
        )

    return [dict(row) for row in rows]
