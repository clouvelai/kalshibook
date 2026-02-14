"""Raw delta query endpoint -- POST /deltas.

Returns paginated orderbook deltas for a market within a time range,
using cursor-based pagination with (ts, id) composite cursor.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime, timezone

import asyncpg
import orjson
from fastapi import APIRouter, Depends, Request

from src.api.deps import get_db_pool, require_credits
from src.api.errors import ValidationError
from src.api.models import DeltaRecord, DeltasRequest, DeltasResponse

router = APIRouter(tags=["Deltas"])


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    """Decode a base64-encoded pagination cursor to (ts, id) tuple.

    Raises ValidationError if the cursor is malformed.
    """
    try:
        payload = base64.b64decode(cursor)
        data = orjson.loads(payload)
        ts = datetime.fromisoformat(data["ts"])
        # Ensure timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts, int(data["id"])
    except Exception:
        raise ValidationError("Invalid pagination cursor.")


def _encode_cursor(ts: datetime, row_id: int) -> str:
    """Encode a (ts, id) tuple into a base64 pagination cursor."""
    payload = orjson.dumps({"ts": ts.isoformat(), "id": row_id})
    return base64.b64encode(payload).decode()


@router.post("/deltas", response_model=DeltasResponse)
async def get_deltas(
    request: Request,
    body: DeltasRequest,
    key: dict = Depends(require_credits(2)),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Query raw orderbook deltas for a market within a time range.

    Uses cursor-based pagination for efficient traversal of large result sets.
    Pass the `next_cursor` from the previous response as `cursor` to fetch
    the next page.
    """
    t0 = time.monotonic()

    # Fetch limit + 1 to determine has_more
    fetch_limit = body.limit + 1

    async with pool.acquire() as conn:
        if body.cursor is not None:
            cursor_ts, cursor_id = _decode_cursor(body.cursor)
            rows = await conn.fetch(
                """
                SELECT id, market_ticker, ts, seq, price_cents, delta_amount, side
                FROM deltas
                WHERE market_ticker = $1 AND ts >= $2 AND ts <= $3
                  AND (ts, id) > ($5, $6)
                ORDER BY ts ASC, id ASC
                LIMIT $4
                """,
                body.market_ticker,
                body.start_time,
                body.end_time,
                fetch_limit,
                cursor_ts,
                cursor_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, market_ticker, ts, seq, price_cents, delta_amount, side
                FROM deltas
                WHERE market_ticker = $1 AND ts >= $2 AND ts <= $3
                ORDER BY ts ASC, id ASC
                LIMIT $4
                """,
                body.market_ticker,
                body.start_time,
                body.end_time,
                fetch_limit,
            )

    # Determine pagination
    has_more = len(rows) > body.limit
    if has_more:
        rows = rows[: body.limit]

    # Build next_cursor from last row
    next_cursor: str | None = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last["ts"], last["id"])

    # Convert rows to response records
    data = [
        DeltaRecord(
            market_ticker=row["market_ticker"],
            ts=row["ts"].isoformat(),
            seq=row["seq"],
            price_cents=row["price_cents"],
            delta_amount=row["delta_amount"],
            side=row["side"],
        )
        for row in rows
    ]

    elapsed = time.monotonic() - t0

    return DeltasResponse(
        data=data,
        next_cursor=next_cursor,
        has_more=has_more,
        request_id=request.state.request_id,
        response_time=round(elapsed, 4),
    )
