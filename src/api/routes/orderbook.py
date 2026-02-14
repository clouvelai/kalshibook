"""Orderbook reconstruction endpoint -- POST /orderbook.

Reconstructs the L2 orderbook state for any market at any historical timestamp
by replaying deltas on top of the nearest prior snapshot.
"""

from __future__ import annotations

import time

import asyncpg
from fastapi import APIRouter, Depends, Request

from src.api.deps import get_api_key, get_db_pool
from src.api.errors import MarketNotFoundError, NoDataAvailableError
from src.api.models import OrderbookRequest, OrderbookResponse
from src.api.services.reconstruction import reconstruct_orderbook

router = APIRouter(tags=["Orderbook"])


@router.post("/orderbook", response_model=OrderbookResponse)
async def get_orderbook(
    request: Request,
    body: OrderbookRequest,
    key: dict = Depends(get_api_key),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Reconstruct the orderbook state at a specific historical timestamp.

    Returns the full yes/no price levels by finding the nearest snapshot
    before the requested timestamp and replaying all subsequent deltas.
    """
    t0 = time.monotonic()

    result = await reconstruct_orderbook(
        pool,
        body.market_ticker,
        body.timestamp,
        body.depth,
    )

    # No data at all for this market
    if result is None:
        raise MarketNotFoundError(body.market_ticker)

    # Market exists but timestamp is before first snapshot
    if result.get("error") == "no_data":
        earliest = result["earliest_available_at"]
        raise NoDataAvailableError(
            f"No data available for '{body.market_ticker}' at the requested timestamp. "
            f"Earliest available data: {earliest}"
        )

    elapsed = time.monotonic() - t0

    return OrderbookResponse(
        market_ticker=result["market_ticker"],
        timestamp=result["timestamp"],
        snapshot_basis=result["snapshot_basis"],
        deltas_applied=result["deltas_applied"],
        yes=result["yes"],
        no=result["no"],
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )
