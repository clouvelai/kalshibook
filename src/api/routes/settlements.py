"""Settlement data endpoints -- GET /settlements, GET /settlements/{ticker}.

Provides access to market settlement/resolution outcomes for backtesting
P&L calculations and strategy evaluation.
"""

from __future__ import annotations

import time

import asyncpg
from fastapi import APIRouter, Depends, Query, Request

from src.api.deps import get_db_pool, require_credits
from src.api.errors import SettlementNotFoundError
from src.api.models import SettlementRecord, SettlementResponse, SettlementsResponse

router = APIRouter(tags=["Settlements"])


@router.get("/settlements", response_model=SettlementsResponse)
async def list_settlements(
    request: Request,
    event_ticker: str | None = Query(default=None, description="Filter by event ticker"),
    result: str | None = Query(default=None, description="Filter by settlement result (yes, no, void, etc.)"),
    key: dict = Depends(require_credits(1)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """List all settlement records.

    Optionally filter by event ticker or settlement result.
    Returns settlements ordered by determination date (most recent first).
    """
    t0 = time.monotonic()

    # Build query dynamically based on filters
    base_query = """
        SELECT market_ticker, event_ticker, result, settlement_value,
               determined_at, settled_at
        FROM settlements
    """
    conditions: list[str] = []
    params: list = []
    param_idx = 1

    if event_ticker is not None:
        conditions.append(f"event_ticker = ${param_idx}")
        params.append(event_ticker)
        param_idx += 1

    if result is not None:
        conditions.append(f"result = ${param_idx}")
        params.append(result)
        param_idx += 1

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY determined_at DESC NULLS LAST"

    async with pool.acquire() as conn:
        rows = await conn.fetch(base_query, *params)

    data = [
        SettlementRecord(
            market_ticker=row["market_ticker"],
            event_ticker=row["event_ticker"],
            result=row["result"],
            settlement_value=row["settlement_value"],
            determined_at=row["determined_at"].isoformat() if row["determined_at"] else None,
            settled_at=row["settled_at"].isoformat() if row["settled_at"] else None,
        )
        for row in rows
    ]

    elapsed = time.monotonic() - t0

    return SettlementsResponse(
        data=data,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )


@router.get("/settlements/{ticker}", response_model=SettlementResponse)
async def get_settlement(
    request: Request,
    ticker: str,
    key: dict = Depends(require_credits(1)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get settlement data for a specific market.

    Returns the settlement result and value for the given market ticker.
    Raises 404 if no settlement data exists for the market.
    """
    t0 = time.monotonic()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT market_ticker, event_ticker, result, settlement_value,
                   determined_at, settled_at
            FROM settlements
            WHERE market_ticker = $1
            """,
            ticker,
        )

    if row is None:
        raise SettlementNotFoundError(ticker)

    data = SettlementRecord(
        market_ticker=row["market_ticker"],
        event_ticker=row["event_ticker"],
        result=row["result"],
        settlement_value=row["settlement_value"],
        determined_at=row["determined_at"].isoformat() if row["determined_at"] else None,
        settled_at=row["settled_at"].isoformat() if row["settled_at"] else None,
    )

    elapsed = time.monotonic() - t0

    return SettlementResponse(
        data=data,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )
