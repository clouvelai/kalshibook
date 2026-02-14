"""Batched database writer for orderbook data."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import asyncpg
import orjson

from src.collector.metrics import get_logger, get_metrics
from src.collector.models import (
    GapRecord,
    OrderbookDelta,
    OrderbookSnapshot,
    OverflowRecord,
)

logger = get_logger("writer")


class DatabaseWriter:
    """Buffers and batch-writes orderbook data to PostgreSQL."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        max_batch_size: int = 500,
        flush_interval: float = 2.0,
    ):
        self._pool = pool
        self._max_batch_size = max_batch_size
        self._flush_interval = flush_interval
        self._metrics = get_metrics()

        # Buffers
        self._snapshot_buffer: list[OrderbookSnapshot] = []
        self._delta_buffer: list[OrderbookDelta] = []
        self._gap_buffer: list[GapRecord] = []
        self._overflow_buffer: list[OverflowRecord] = []
        self._market_updates: list[dict] = []

        self._lock = asyncio.Lock()
        self._running = False

    async def add_snapshot(self, snapshot: OrderbookSnapshot) -> None:
        """Add a snapshot to the write buffer."""
        async with self._lock:
            self._snapshot_buffer.append(snapshot)
            if len(self._snapshot_buffer) >= self._max_batch_size:
                await self._flush_snapshots()

    async def add_delta(self, delta: OrderbookDelta) -> None:
        """Add a delta to the write buffer."""
        async with self._lock:
            self._delta_buffer.append(delta)
            if len(self._delta_buffer) >= self._max_batch_size:
                await self._flush_deltas()

    async def add_gap(self, gap: GapRecord) -> None:
        """Add a gap record to the write buffer."""
        async with self._lock:
            self._gap_buffer.append(gap)

    async def add_overflow(self, overflow: OverflowRecord) -> None:
        """Add an overflow record to the write buffer."""
        async with self._lock:
            self._overflow_buffer.append(overflow)

    async def add_market_update(self, market: dict) -> None:
        """Add a market upsert to the write buffer."""
        async with self._lock:
            self._market_updates.append(market)

    async def start_flush_loop(self) -> None:
        """Run the periodic flush loop. Call as a background task."""
        self._running = True
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self.flush_all()

    async def flush_all(self) -> None:
        """Flush all non-empty buffers."""
        async with self._lock:
            tasks = []
            if self._snapshot_buffer:
                tasks.append(self._flush_snapshots())
            if self._delta_buffer:
                tasks.append(self._flush_deltas())
            if self._gap_buffer:
                tasks.append(self._flush_gaps())
            if self._overflow_buffer:
                tasks.append(self._flush_overflow())
            if self._market_updates:
                tasks.append(self._flush_market_updates())
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _flush_snapshots(self) -> None:
        """Write buffered snapshots to database."""
        if not self._snapshot_buffer:
            return
        batch = self._snapshot_buffer[:]
        self._snapshot_buffer.clear()

        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO snapshots
                        (market_ticker, captured_at, seq, yes_levels, no_levels, source)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    [
                        (
                            s.market_ticker,
                            s.ts,
                            s.seq,
                            orjson.dumps(s.yes).decode(),
                            orjson.dumps(s.no).decode(),
                            "ws_subscribe",
                        )
                        for s in batch
                    ],
                )
            self._metrics.snapshots_stored += len(batch)
            logger.debug("snapshots_flushed", count=len(batch))
        except Exception:
            # Put back on failure
            self._snapshot_buffer = batch + self._snapshot_buffer
            logger.exception("snapshot_flush_failed", count=len(batch))

    async def _flush_deltas(self) -> None:
        """Write buffered deltas to database."""
        if not self._delta_buffer:
            return
        batch = self._delta_buffer[:]
        self._delta_buffer.clear()

        try:
            async with self._pool.acquire() as conn:
                # Ensure partition exists for all dates in batch
                dates_seen = {d.ts.date() for d in batch}
                for dt in dates_seen:
                    await self._ensure_delta_partition(conn, dt)

                await conn.executemany(
                    """
                    INSERT INTO deltas
                        (market_ticker, ts, seq, sid, price_cents, delta_amount, side)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    [
                        (
                            d.market_ticker,
                            d.ts,
                            d.seq,
                            d.sid,
                            d.price,
                            d.delta,
                            d.side,
                        )
                        for d in batch
                    ],
                )
            self._metrics.record_deltas_stored(len(batch))
            logger.debug("deltas_flushed", count=len(batch))
        except Exception:
            self._delta_buffer = batch + self._delta_buffer
            logger.exception("delta_flush_failed", count=len(batch))

    async def _flush_gaps(self) -> None:
        """Write buffered gap records to database."""
        if not self._gap_buffer:
            return
        batch = self._gap_buffer[:]
        self._gap_buffer.clear()

        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO sequence_gaps
                        (market_ticker, detected_at, expected_seq, received_seq, sid)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [
                        (g.market_ticker, g.detected_at, g.expected_seq, g.received_seq, g.sid)
                        for g in batch
                    ],
                )
            logger.info("gaps_flushed", count=len(batch))
        except Exception:
            self._gap_buffer = batch + self._gap_buffer
            logger.exception("gap_flush_failed", count=len(batch))

    async def _flush_overflow(self) -> None:
        """Write buffered overflow records to database."""
        if not self._overflow_buffer:
            return
        batch = self._overflow_buffer[:]
        self._overflow_buffer.clear()

        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO subscription_overflow (market_ticker, event_ticker, reason)
                    VALUES ($1, $2, $3)
                    """,
                    [(o.market_ticker, o.event_ticker, o.reason) for o in batch],
                )
            logger.info("overflow_flushed", count=len(batch))
        except Exception:
            self._overflow_buffer = batch + self._overflow_buffer
            logger.exception("overflow_flush_failed", count=len(batch))

    async def _flush_market_updates(self) -> None:
        """Upsert buffered market updates to database."""
        if not self._market_updates:
            return
        batch = self._market_updates[:]
        self._market_updates.clear()

        try:
            async with self._pool.acquire() as conn:
                for m in batch:
                    await conn.execute(
                        """
                        INSERT INTO markets (ticker, status, metadata)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (ticker) DO UPDATE SET
                            status = EXCLUDED.status,
                            metadata = COALESCE(EXCLUDED.metadata, markets.metadata),
                            last_updated = now()
                        """,
                        m.get("ticker", ""),
                        m.get("event_type", "active"),
                        orjson.dumps(m.get("metadata", {})).decode()
                        if m.get("metadata")
                        else None,
                    )
            logger.debug("markets_flushed", count=len(batch))
        except Exception:
            self._market_updates = batch + self._market_updates
            logger.exception("market_flush_failed", count=len(batch))

    @staticmethod
    async def _ensure_delta_partition(conn: asyncpg.Connection, dt) -> None:
        """Create a delta partition for a specific date if it doesn't exist."""
        partition_name = f"deltas_{dt.strftime('%Y_%m_%d')}"
        start = dt.strftime("%Y-%m-%d")
        end = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

        await conn.execute(f"""
            DO $$
            BEGIN
                CREATE TABLE IF NOT EXISTS {partition_name}
                    PARTITION OF deltas
                    FOR VALUES FROM ('{start}') TO ('{end}');
            EXCEPTION WHEN duplicate_table THEN
                NULL;
            END $$;
        """)

    async def stop(self) -> None:
        """Stop the flush loop and do a final flush."""
        self._running = False
        await self.flush_all()
        logger.info("writer_stopped")

    @property
    def buffer_sizes(self) -> dict:
        """Return current buffer sizes for monitoring."""
        return {
            "snapshots": len(self._snapshot_buffer),
            "deltas": len(self._delta_buffer),
            "gaps": len(self._gap_buffer),
            "overflow": len(self._overflow_buffer),
            "markets": len(self._market_updates),
        }
