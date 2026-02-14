"""Market listing and detail endpoints -- GET /markets, GET /markets/{ticker}.

Provides discovery of available markets and their data coverage dates
so clients know which markets have historical orderbook data and for what periods.
"""

from __future__ import annotations

import time

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.api.deps import get_api_key, get_db_pool
from src.api.errors import MarketNotFoundError
from src.api.models import MarketDetail, MarketDetailResponse, MarketsResponse, MarketSummary

router = APIRouter(tags=["Markets"])


@router.get("/markets", response_model=MarketsResponse)
async def list_markets(
    request: Request,
    key: dict = Depends(get_api_key),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """List all markets with data coverage dates.

    Returns every market the system has discovered, including the earliest
    and latest data timestamps from snapshots and deltas.
    """
    t0 = time.monotonic()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.ticker, m.title, m.event_ticker, m.status, m.category,
              (SELECT MIN(captured_at) FROM snapshots
               WHERE market_ticker = m.ticker) AS first_data_at,
              (SELECT MAX(ts) FROM deltas
               WHERE market_ticker = m.ticker) AS last_data_at
            FROM markets m
            ORDER BY m.discovered_at DESC
            """
        )

    data = [
        MarketSummary(
            ticker=row["ticker"],
            title=row["title"],
            event_ticker=row["event_ticker"],
            status=row["status"],
            category=row["category"],
            first_data_at=row["first_data_at"].isoformat() if row["first_data_at"] else None,
            last_data_at=row["last_data_at"].isoformat() if row["last_data_at"] else None,
        )
        for row in rows
    ]

    elapsed = time.monotonic() - t0

    return MarketsResponse(
        data=data,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )


@router.get("/markets/{ticker}", response_model=MarketDetailResponse)
async def get_market_detail(
    request: Request,
    ticker: str,
    key: dict = Depends(get_api_key),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get full detail for a single market, including metadata and data counts.

    Returns the market's metadata from the Kalshi API along with snapshot/delta
    counts and data coverage dates.
    """
    t0 = time.monotonic()

    async with pool.acquire() as conn:
        market = await conn.fetchrow(
            """
            SELECT ticker, title, event_ticker, status, category,
                   rules, strike_price, discovered_at, metadata
            FROM markets
            WHERE ticker = $1
            """,
            ticker,
        )

        if market is None:
            raise MarketNotFoundError(ticker)

        # Get counts and coverage dates
        stats = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM snapshots WHERE market_ticker = $1) AS snapshot_count,
              (SELECT COUNT(*) FROM deltas WHERE market_ticker = $1) AS delta_count,
              (SELECT MIN(captured_at) FROM snapshots WHERE market_ticker = $1) AS first_data_at,
              (SELECT MAX(ts) FROM deltas WHERE market_ticker = $1) AS last_data_at
            """,
            ticker,
        )

    detail = MarketDetail(
        ticker=market["ticker"],
        title=market["title"],
        event_ticker=market["event_ticker"],
        status=market["status"],
        category=market["category"],
        rules=market["rules"],
        strike_price=float(market["strike_price"]) if market["strike_price"] is not None else None,
        discovered_at=market["discovered_at"].isoformat(),
        metadata=market["metadata"],
        snapshot_count=stats["snapshot_count"],
        delta_count=stats["delta_count"],
        first_data_at=stats["first_data_at"].isoformat() if stats["first_data_at"] else None,
        last_data_at=stats["last_data_at"].isoformat() if stats["last_data_at"] else None,
    )

    elapsed = time.monotonic() - t0

    return MarketDetailResponse(
        data=detail,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )
