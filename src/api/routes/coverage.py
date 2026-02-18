"""Coverage discovery endpoints -- GET /coverage/stats, POST /coverage/refresh.

Serves pre-computed market data coverage segments from a materialized view,
grouped by event for the dashboard. No credits deducted (JWT auth only).
"""

from __future__ import annotations

import time
from collections import defaultdict

import asyncpg
from fastapi import APIRouter, Depends, Query, Request

from src.api.deps import get_authenticated_user, get_db_pool
from src.api.models import (
    CoverageSegment,
    CoverageStatsResponse,
    CoverageSummary,
    EventCoverageGroup,
    MarketCoverage,
)

router = APIRouter(tags=["Coverage"])


@router.get("/coverage/stats", response_model=CoverageStatsResponse)
async def get_coverage_stats(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
    search: str | None = Query(default=None, description="Search market ticker or title (ILIKE)"),
    status: str | None = Query(default=None, description="Filter by market status"),
    event_ticker: str | None = Query(default=None, description="Filter by event ticker"),
    page: int = Query(default=1, ge=1, description="Page number (event-level pagination)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Events per page"),
):
    """Return per-market coverage segments grouped by event.

    Reads from the pre-computed ``market_coverage_stats`` materialized view
    joined with market and event metadata. Pagination is at the event-group
    level. Markets with no event_ticker are grouped under "Ungrouped".
    """
    t0 = time.monotonic()

    # Build dynamic WHERE clause
    conditions: list[str] = []
    params: list[object] = []
    idx = 1

    if search:
        conditions.append(f"(m.ticker ILIKE ${idx} OR m.title ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1

    if status:
        conditions.append(f"m.status = ${idx}")
        params.append(status)
        idx += 1

    if event_ticker:
        conditions.append(f"m.event_ticker = ${idx}")
        params.append(event_ticker)
        idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT
            cs.market_ticker,
            cs.segment_id,
            cs.segment_start,
            cs.segment_end,
            cs.days_covered,
            cs.snapshot_count,
            cs.delta_count,
            cs.trade_count,
            m.title AS market_title,
            m.status AS market_status,
            m.event_ticker,
            e.title AS event_title
        FROM market_coverage_stats cs
        JOIN markets m ON m.ticker = cs.market_ticker
        LEFT JOIN events e ON e.event_ticker = m.event_ticker
        {where_clause}
        ORDER BY m.event_ticker NULLS LAST, cs.market_ticker, cs.segment_id
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    # Group rows by market, then by event
    markets_map: dict[str, dict] = {}
    for row in rows:
        ticker = row["market_ticker"]
        if ticker not in markets_map:
            markets_map[ticker] = {
                "ticker": ticker,
                "title": row["market_title"],
                "status": row["market_status"],
                "event_ticker": row["event_ticker"],
                "event_title": row["event_title"],
                "segments": [],
            }
        markets_map[ticker]["segments"].append(
            CoverageSegment(
                segment_id=row["segment_id"],
                segment_start=str(row["segment_start"]),
                segment_end=str(row["segment_end"]),
                days_covered=row["days_covered"],
                snapshot_count=row["snapshot_count"],
                delta_count=row["delta_count"],
                trade_count=row["trade_count"],
            )
        )

    # Build MarketCoverage objects
    market_coverages: list[MarketCoverage] = []
    for mkt in markets_map.values():
        segs = mkt["segments"]
        market_coverages.append(
            MarketCoverage(
                ticker=mkt["ticker"],
                title=mkt["title"],
                status=mkt["status"],
                segment_count=len(segs),
                total_snapshots=sum(s.snapshot_count for s in segs),
                total_deltas=sum(s.delta_count for s in segs),
                total_trades=sum(s.trade_count for s in segs),
                first_date=segs[0].segment_start if segs else None,
                last_date=segs[-1].segment_end if segs else None,
                segments=segs,
            )
        )

    # Group markets by event
    event_groups: dict[str, dict] = defaultdict(lambda: {"markets": [], "event_title": None})
    for mc in market_coverages:
        mkt_info = markets_map[mc.ticker]
        evt = mkt_info["event_ticker"] or "__ungrouped__"
        event_groups[evt]["markets"].append(mc)
        if mkt_info["event_title"]:
            event_groups[evt]["event_title"] = mkt_info["event_title"]

    # Build event coverage group list, ungrouped at bottom
    all_events: list[EventCoverageGroup] = []
    ungrouped: EventCoverageGroup | None = None

    for evt_ticker, grp in sorted(event_groups.items(), key=lambda x: x[0]):
        ecg = EventCoverageGroup(
            event_ticker=evt_ticker if evt_ticker != "__ungrouped__" else "Ungrouped",
            event_title=grp["event_title"] if evt_ticker != "__ungrouped__" else "Ungrouped Markets",
            market_count=len(grp["markets"]),
            markets=grp["markets"],
        )
        if evt_ticker == "__ungrouped__":
            ungrouped = ecg
        else:
            all_events.append(ecg)

    if ungrouped:
        all_events.append(ungrouped)

    total_events = len(all_events)

    # Event-level pagination
    start = (page - 1) * page_size
    paged_events = all_events[start : start + page_size]

    # Compute summary from ALL markets (not just paged)
    all_dates: list[str] = []
    total_snapshots = 0
    total_deltas = 0
    for mc in market_coverages:
        total_snapshots += mc.total_snapshots
        total_deltas += mc.total_deltas
        if mc.first_date:
            all_dates.append(mc.first_date)
        if mc.last_date:
            all_dates.append(mc.last_date)

    summary = CoverageSummary(
        total_markets=len(market_coverages),
        total_snapshots=total_snapshots,
        total_deltas=total_deltas,
        date_range_start=min(all_dates) if all_dates else None,
        date_range_end=max(all_dates) if all_dates else None,
    )

    elapsed = time.monotonic() - t0

    return CoverageStatsResponse(
        summary=summary,
        events=paged_events,
        total_events=total_events,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )


@router.post("/coverage/refresh")
async def refresh_coverage(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Trigger a concurrent refresh of the coverage materialized view.

    Uses an advisory lock to prevent overlapping refreshes.
    """
    async with pool.acquire() as conn:
        await conn.execute("SELECT refresh_coverage_stats()")

    return {
        "message": "Coverage stats refreshed",
        "request_id": request.state.request_id,
    }
