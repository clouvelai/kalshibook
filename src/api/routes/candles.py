"""Candlestick data endpoint -- GET /candles/{ticker}.

Returns OHLCV candlestick data at 1-minute, 1-hour, and 1-day intervals,
computed from raw trade data via SQL aggregation (not proxied from Kalshi).
"""

from __future__ import annotations

import time
from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, Query, Request

from src.api.deps import get_db_pool, require_credits
from src.api.errors import ValidationError
from src.api.models import CandleRecord, CandlesResponse
from src.api.services.candles import VALID_INTERVALS, get_candles

router = APIRouter(tags=["Candles"])


@router.get("/candles/{ticker}", response_model=CandlesResponse)
async def get_candles_endpoint(
    request: Request,
    ticker: str,
    start_time: datetime = Query(..., description="Start of time range (ISO 8601, inclusive)"),
    end_time: datetime = Query(..., description="End of time range (ISO 8601, exclusive)"),
    interval: str = Query(default="1h", description="Candle interval: 1m, 1h, or 1d"),
    key: dict = Depends(require_credits(3)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get OHLCV candlestick data for a market.

    Computes open, high, low, close prices and volume from raw trade data
    using SQL aggregation at the requested interval.

    Buckets with no trades produce no rows. Consumers typically forward-fill
    the previous close price for empty intervals.

    Credit cost: 3 (aggregation query, moderate compute).
    """
    t0 = time.monotonic()

    if interval not in VALID_INTERVALS:
        raise ValidationError(
            f"Invalid interval '{interval}'. Must be one of: {', '.join(sorted(VALID_INTERVALS.keys()))}"
        )

    pg_interval = VALID_INTERVALS[interval]
    rows = await get_candles(pool, ticker, start_time, end_time, pg_interval)

    data = [
        CandleRecord(
            bucket=row["bucket"].isoformat(),
            market_ticker=row["market_ticker"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            trade_count=row["trade_count"],
        )
        for row in rows
    ]

    elapsed = time.monotonic() - t0

    return CandlesResponse(
        data=data,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )
