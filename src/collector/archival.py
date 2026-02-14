"""Data archival: move old orderbook data from Postgres to Parquet in Supabase Storage."""

from __future__ import annotations

import asyncio
import io
from datetime import date, datetime, timedelta, timezone

import asyncpg
import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from src.collector.metrics import get_logger
from src.shared.config import Settings, get_settings
from src.shared.db import create_pool

logger = get_logger("archival")


class ArchivalJob:
    """Archives old orderbook data to Parquet files in Supabase Storage."""

    def __init__(self, pool: asyncpg.Pool, settings: Settings):
        self._pool = pool
        self._settings = settings
        self._storage_url = f"{settings.supabase_url}/storage/v1"
        self._headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        }

    async def run(self, dry_run: bool = False) -> dict:
        """Run the archival process. Returns summary stats."""
        cutoff = date.today() - timedelta(days=self._settings.hot_storage_days)
        logger.info("archival_started", cutoff=cutoff.isoformat(), dry_run=dry_run)

        stats = {"days_archived": 0, "deltas_archived": 0, "snapshots_archived": 0}

        # Find dates with data older than cutoff
        async with self._pool.acquire() as conn:
            dates_with_data = await conn.fetch(
                """
                SELECT DISTINCT ts::date AS data_date
                FROM deltas
                WHERE ts < $1
                ORDER BY data_date
                """,
                datetime.combine(cutoff, datetime.min.time()).replace(tzinfo=timezone.utc),
            )

        for row in dates_with_data:
            data_date = row["data_date"]
            result = await self._archive_date(data_date, dry_run)
            stats["days_archived"] += 1
            stats["deltas_archived"] += result.get("deltas", 0)
            stats["snapshots_archived"] += result.get("snapshots", 0)

        logger.info("archival_completed", **stats)
        return stats

    async def _archive_date(self, data_date: date, dry_run: bool) -> dict:
        """Archive all data for a specific date."""
        logger.info("archiving_date", date=data_date.isoformat())
        result = {"deltas": 0, "snapshots": 0}

        start_ts = datetime.combine(data_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_ts = start_ts + timedelta(days=1)

        async with self._pool.acquire() as conn:
            # Fetch deltas grouped by event_ticker
            deltas = await conn.fetch(
                """
                SELECT d.market_ticker, d.ts, d.seq, d.sid, d.price_cents,
                       d.delta_amount, d.side, d.received_at,
                       COALESCE(m.event_ticker, 'unknown') AS event_ticker
                FROM deltas d
                LEFT JOIN markets m ON d.market_ticker = m.ticker
                WHERE d.ts >= $1 AND d.ts < $2
                ORDER BY d.ts
                """,
                start_ts,
                end_ts,
            )

            # Fetch snapshots for the date
            snapshots = await conn.fetch(
                """
                SELECT market_ticker, captured_at, seq, yes_levels, no_levels, source
                FROM snapshots
                WHERE captured_at >= $1 AND captured_at < $2
                ORDER BY captured_at
                """,
                start_ts,
                end_ts,
            )

        if not deltas and not snapshots:
            logger.info("no_data_to_archive", date=data_date.isoformat())
            return result

        if dry_run:
            logger.info(
                "dry_run_would_archive",
                date=data_date.isoformat(),
                deltas=len(deltas),
                snapshots=len(snapshots),
            )
            return {"deltas": len(deltas), "snapshots": len(snapshots)}

        # Ensure storage bucket exists
        await self._ensure_bucket()

        # Archive deltas by event_ticker
        if deltas:
            events = {}
            for row in deltas:
                et = row["event_ticker"]
                events.setdefault(et, []).append(row)

            for event_ticker, event_deltas in events.items():
                parquet_bytes = self._deltas_to_parquet(event_deltas)
                path = (
                    f"archives/{data_date.year}/{data_date.month:02d}/"
                    f"{data_date.day:02d}/deltas_{event_ticker}.parquet"
                )
                await self._upload_to_storage(path, parquet_bytes)
                result["deltas"] += len(event_deltas)

        # Archive snapshots
        if snapshots:
            parquet_bytes = self._snapshots_to_parquet(snapshots)
            path = (
                f"archives/{data_date.year}/{data_date.month:02d}/"
                f"{data_date.day:02d}/snapshots.parquet"
            )
            await self._upload_to_storage(path, parquet_bytes)
            result["snapshots"] = len(snapshots)

        # Delete archived data from Postgres
        await self._delete_archived_data(data_date, start_ts, end_ts)

        logger.info("date_archived", date=data_date.isoformat(), **result)
        return result

    @staticmethod
    def _deltas_to_parquet(rows: list) -> bytes:
        """Convert delta rows to Parquet bytes."""
        table = pa.table(
            {
                "market_ticker": pa.array([r["market_ticker"] for r in rows], type=pa.string()),
                "ts": pa.array([r["ts"] for r in rows], type=pa.timestamp("us", tz="UTC")),
                "seq": pa.array([r["seq"] for r in rows], type=pa.int64()),
                "sid": pa.array([r["sid"] for r in rows], type=pa.int64()),
                "price_cents": pa.array([r["price_cents"] for r in rows], type=pa.int32()),
                "delta_amount": pa.array([r["delta_amount"] for r in rows], type=pa.int32()),
                "side": pa.array([r["side"] for r in rows], type=pa.string()),
                "received_at": pa.array(
                    [r["received_at"] for r in rows], type=pa.timestamp("us", tz="UTC")
                ),
                "event_ticker": pa.array(
                    [r["event_ticker"] for r in rows], type=pa.string()
                ),
            }
        )
        buf = io.BytesIO()
        pq.write_table(table, buf, compression="snappy")
        return buf.getvalue()

    @staticmethod
    def _snapshots_to_parquet(rows: list) -> bytes:
        """Convert snapshot rows to Parquet bytes."""
        table = pa.table(
            {
                "market_ticker": pa.array([r["market_ticker"] for r in rows], type=pa.string()),
                "captured_at": pa.array(
                    [r["captured_at"] for r in rows], type=pa.timestamp("us", tz="UTC")
                ),
                "seq": pa.array([r["seq"] for r in rows], type=pa.int64()),
                "yes_levels": pa.array([str(r["yes_levels"]) for r in rows], type=pa.string()),
                "no_levels": pa.array([str(r["no_levels"]) for r in rows], type=pa.string()),
                "source": pa.array([r["source"] for r in rows], type=pa.string()),
            }
        )
        buf = io.BytesIO()
        pq.write_table(table, buf, compression="snappy")
        return buf.getvalue()

    async def _upload_to_storage(self, path: str, data: bytes) -> None:
        """Upload a file to Supabase Storage."""
        url = f"{self._storage_url}/object/{self._settings.archive_bucket}/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                content=data,
                headers={
                    **self._headers,
                    "Content-Type": "application/octet-stream",
                    "x-upsert": "true",
                },
            )
            resp.raise_for_status()
        logger.debug("uploaded_to_storage", path=path, size_bytes=len(data))

    async def _ensure_bucket(self) -> None:
        """Create the archive bucket if it doesn't exist."""
        url = f"{self._storage_url}/bucket"
        async with httpx.AsyncClient() as client:
            # Try to create - ignore if already exists
            resp = await client.post(
                url,
                json={
                    "id": self._settings.archive_bucket,
                    "name": self._settings.archive_bucket,
                    "public": False,
                },
                headers=self._headers,
            )
            if resp.status_code not in (200, 201, 409):
                resp.raise_for_status()

    async def _delete_archived_data(
        self, data_date: date, start_ts: datetime, end_ts: datetime
    ) -> None:
        """Delete archived data from Postgres. Try dropping partition first, fall back to DELETE."""
        partition_name = f"deltas_{data_date.strftime('%Y_%m_%d')}"

        async with self._pool.acquire() as conn:
            # Try to detach and drop the daily partition
            try:
                await conn.execute(
                    f"ALTER TABLE deltas DETACH PARTITION {partition_name}"
                )
                await conn.execute(f"DROP TABLE {partition_name}")
                logger.info("partition_dropped", partition=partition_name)
            except asyncpg.UndefinedTableError:
                # No partition - fall back to DELETE
                deleted = await conn.execute(
                    "DELETE FROM deltas WHERE ts >= $1 AND ts < $2",
                    start_ts,
                    end_ts,
                )
                logger.info("deltas_deleted_by_range", range_start=start_ts, result=deleted)

            # Delete archived snapshots
            deleted = await conn.execute(
                "DELETE FROM snapshots WHERE captured_at >= $1 AND captured_at < $2",
                start_ts,
                end_ts,
            )
            logger.info("snapshots_deleted", range_start=start_ts, result=deleted)


async def run_archival(settings: Settings | None = None) -> None:
    """Standalone entry point for running archival."""
    if settings is None:
        settings = get_settings()

    pool = await create_pool(
        settings.database_url,
        min_size=2,
        max_size=5,
    )
    try:
        job = ArchivalJob(pool, settings)
        await job.run()
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_archival())
