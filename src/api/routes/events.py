"""Event hierarchy endpoints -- GET /events, GET /events/{event_ticker}.

Navigate the Series > Event > Market hierarchy for multi-market analysis
(e.g., all strike prices for an event).
"""

from __future__ import annotations

import time

import asyncpg
from fastapi import APIRouter, Depends, Query, Request

from src.api.deps import get_db_pool, require_credits
from src.api.errors import EventNotFoundError
from src.api.models import (
    EventDetail,
    EventDetailResponse,
    EventsResponse,
    EventSummary,
    MarketSummary,
)

router = APIRouter(tags=["Events"])


@router.get("/events", response_model=EventsResponse)
async def list_events(
    request: Request,
    category: str | None = Query(default=None, description="Filter by event category"),
    series_ticker: str | None = Query(default=None, description="Filter by parent series ticker"),
    status: str | None = Query(default=None, description="Filter by event status"),
    key: dict = Depends(require_credits(1)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """List events with market counts.

    Optionally filter by category, series_ticker, or status.
    Returns events ordered by event_ticker.

    Credit cost: 1.
    """
    t0 = time.monotonic()

    # Build query dynamically based on filters
    base_query = """
        SELECT e.event_ticker, e.series_ticker, e.title, e.sub_title,
               e.category, e.mutually_exclusive, e.status,
               (SELECT COUNT(*) FROM markets WHERE event_ticker = e.event_ticker) AS market_count
        FROM events e
    """
    conditions: list[str] = []
    params: list = []
    param_idx = 1

    if category is not None:
        conditions.append(f"e.category = ${param_idx}")
        params.append(category)
        param_idx += 1

    if series_ticker is not None:
        conditions.append(f"e.series_ticker = ${param_idx}")
        params.append(series_ticker)
        param_idx += 1

    if status is not None:
        conditions.append(f"e.status = ${param_idx}")
        params.append(status)
        param_idx += 1

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY e.event_ticker"

    async with pool.acquire() as conn:
        rows = await conn.fetch(base_query, *params)

    data = [
        EventSummary(
            event_ticker=row["event_ticker"],
            series_ticker=row["series_ticker"],
            title=row["title"],
            sub_title=row["sub_title"],
            category=row["category"],
            mutually_exclusive=row["mutually_exclusive"],
            status=row["status"],
            market_count=row["market_count"],
        )
        for row in rows
    ]

    elapsed = time.monotonic() - t0

    return EventsResponse(
        data=data,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )


@router.get("/events/{event_ticker}", response_model=EventDetailResponse)
async def get_event_detail(
    request: Request,
    event_ticker: str,
    key: dict = Depends(require_credits(1)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get event detail with nested markets.

    Returns the event metadata along with all markets belonging to this event.
    Enables multi-market analysis (e.g., all strike prices for an event).

    Credit cost: 1.
    """
    t0 = time.monotonic()

    async with pool.acquire() as conn:
        event = await conn.fetchrow(
            """
            SELECT event_ticker, series_ticker, title, sub_title,
                   category, mutually_exclusive, status
            FROM events
            WHERE event_ticker = $1
            """,
            event_ticker,
        )

        if event is None:
            raise EventNotFoundError(event_ticker)

        market_rows = await conn.fetch(
            """
            SELECT ticker, title, event_ticker, status, category
            FROM markets
            WHERE event_ticker = $1
            ORDER BY ticker
            """,
            event_ticker,
        )

    markets = [
        MarketSummary(
            ticker=row["ticker"],
            title=row["title"],
            event_ticker=row["event_ticker"],
            status=row["status"],
            category=row["category"],
        )
        for row in market_rows
    ]

    data = EventDetail(
        event_ticker=event["event_ticker"],
        series_ticker=event["series_ticker"],
        title=event["title"],
        sub_title=event["sub_title"],
        category=event["category"],
        mutually_exclusive=event["mutually_exclusive"],
        status=event["status"],
        market_count=len(markets),
        markets=markets,
    )

    elapsed = time.monotonic() - t0

    return EventDetailResponse(
        data=data,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )
