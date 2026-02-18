"""Playground endpoints -- GET /playground/markets, POST /playground/demo.

Zero-credit demo endpoints for the API playground. Market search provides
autocomplete against the coverage materialized view. Demo execution routes
to existing service functions without deducting credits.
"""

from __future__ import annotations

import time

import asyncpg
from fastapi import APIRouter, Depends, Query, Request

from src.api.deps import get_authenticated_user, get_db_pool
from src.api.errors import (
    MarketNotFoundError,
    NoDataAvailableError,
    ValidationError,
)
from src.api.models import (
    DemoRequest,
    DemoResponse,
    PlaygroundMarketResult,
    PlaygroundMarketsResponse,
)
from src.api.services.candles import VALID_INTERVALS, get_candles
from src.api.services.reconstruction import reconstruct_orderbook

router = APIRouter(tags=["Playground"])


@router.get("/playground/markets", response_model=PlaygroundMarketsResponse)
async def search_playground_markets(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
    q: str = Query(default="", description="Search query (ticker or title substring)"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results to return"),
):
    """Search markets with confirmed data coverage for playground autocomplete.

    Queries the pre-computed ``market_coverage_stats`` materialized view joined
    with market metadata. Returns markets ordered by most recent coverage data.
    """
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if q:
        conditions.append(f"(m.ticker ILIKE ${idx} OR m.title ILIKE ${idx})")
        params.append(f"%{q}%")
        idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT
            m.ticker,
            m.title,
            m.status,
            m.event_ticker,
            MIN(cs.segment_start)::text AS first_date,
            MAX(cs.segment_end)::text AS last_date
        FROM market_coverage_stats cs
        JOIN markets m ON m.ticker = cs.market_ticker
        {where_clause}
        GROUP BY m.ticker, m.title, m.status, m.event_ticker
        ORDER BY MAX(cs.segment_end) DESC
        LIMIT ${idx}
    """
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    data = [
        PlaygroundMarketResult(
            ticker=row["ticker"],
            title=row["title"],
            status=row["status"],
            event_ticker=row["event_ticker"],
            first_date=row["first_date"],
            last_date=row["last_date"],
        )
        for row in rows
    ]

    return PlaygroundMarketsResponse(
        data=data,
        request_id=request.state.request_id,
    )


@router.post("/playground/demo", response_model=DemoResponse)
async def execute_demo(
    request: Request,
    body: DemoRequest,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Execute a zero-credit demo query for the playground.

    Routes to existing service functions (orderbook reconstruction, trades
    query, candle aggregation) without deducting credits.
    """
    t0 = time.monotonic()

    if body.endpoint == "orderbook":
        if body.timestamp is None:
            raise ValidationError("timestamp is required for orderbook demo")

        result = await reconstruct_orderbook(
            pool, body.market_ticker, body.timestamp, body.depth or 10
        )
        if result is None:
            raise MarketNotFoundError(body.market_ticker)
        if result.get("error") == "no_data":
            raise NoDataAvailableError(
                f"No orderbook data available for {body.market_ticker} at {body.timestamp.isoformat()}"
            )

        elapsed = time.monotonic() - t0
        return DemoResponse(
            endpoint="orderbook",
            data=result,
            response_time=round(elapsed, 4),
            request_id=request.state.request_id,
        )

    elif body.endpoint == "trades":
        if body.start_time is None or body.end_time is None:
            raise ValidationError("start_time and end_time are required for trades demo")

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT trade_id, market_ticker, yes_price, no_price,
                       count, taker_side, ts
                FROM trades
                WHERE market_ticker = $1 AND ts >= $2 AND ts < $3
                ORDER BY ts ASC
                LIMIT $4
                """,
                body.market_ticker,
                body.start_time,
                body.end_time,
                body.limit,
            )

        data = [
            {
                "trade_id": row["trade_id"],
                "market_ticker": row["market_ticker"],
                "yes_price": row["yes_price"],
                "no_price": row["no_price"],
                "count": row["count"],
                "taker_side": row["taker_side"],
                "ts": row["ts"].isoformat(),
            }
            for row in rows
        ]

        elapsed = time.monotonic() - t0
        return DemoResponse(
            endpoint="trades",
            data=data,
            response_time=round(elapsed, 4),
            request_id=request.state.request_id,
        )

    elif body.endpoint == "candles":
        if body.start_time is None or body.end_time is None:
            raise ValidationError("start_time and end_time are required for candles demo")

        pg_interval = VALID_INTERVALS.get(body.interval or "1h", "hour")
        rows = await get_candles(
            pool, body.market_ticker, body.start_time, body.end_time, pg_interval
        )

        # Convert datetime objects to ISO strings for JSON serialization
        data = []
        for row in rows:
            entry = dict(row)
            if hasattr(entry.get("bucket"), "isoformat"):
                entry["bucket"] = entry["bucket"].isoformat()
            data.append(entry)

        elapsed = time.monotonic() - t0
        return DemoResponse(
            endpoint="candles",
            data=data,
            response_time=round(elapsed, 4),
            request_id=request.state.request_id,
        )

    else:
        raise ValidationError(
            "Invalid endpoint. Must be one of: orderbook, trades, candles"
        )
