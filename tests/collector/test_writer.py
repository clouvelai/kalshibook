"""Tests for batched database writer."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.collector.models import GapRecord, OrderbookDelta, OrderbookSnapshot, OverflowRecord
from src.collector.writer import DatabaseWriter


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = mock_ctx
    return pool


@pytest.fixture
def writer(mock_pool):
    return DatabaseWriter(pool=mock_pool, max_batch_size=3, flush_interval=1.0)


def make_delta(ticker="TEST-MKT", seq=1, sid=100, price=50, delta=5, side="yes"):
    return OrderbookDelta(
        market_ticker=ticker,
        seq=seq,
        sid=sid,
        price=price,
        delta=delta,
        side=side,
        ts=datetime(2024, 2, 13, 12, 0, 0, tzinfo=timezone.utc),
    )


def make_snapshot(ticker="TEST-MKT", seq=1, sid=100):
    return OrderbookSnapshot(
        market_ticker=ticker,
        seq=seq,
        sid=sid,
        yes=[[50, 10], [55, 5]],
        no=[[45, 8]],
        ts=datetime(2024, 2, 13, 12, 0, 0, tzinfo=timezone.utc),
    )


async def test_delta_buffer_flushes_on_size(writer, mock_pool):
    # max_batch_size=3, adding 3 deltas should trigger flush
    await writer.add_delta(make_delta(seq=1))
    await writer.add_delta(make_delta(seq=2))

    # Buffer should have 2 items, no flush yet
    assert writer.buffer_sizes["deltas"] == 2
    mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
    mock_conn.executemany.assert_not_awaited()

    # Third delta triggers flush
    await writer.add_delta(make_delta(seq=3))
    assert writer.buffer_sizes["deltas"] == 0


async def test_snapshot_added_to_buffer(writer):
    snapshot = make_snapshot()
    await writer.add_snapshot(snapshot)
    assert writer.buffer_sizes["snapshots"] == 1


async def test_snapshot_buffer_flushes_on_size(writer, mock_pool):
    # max_batch_size=3
    await writer.add_snapshot(make_snapshot(seq=1))
    await writer.add_snapshot(make_snapshot(seq=2))
    assert writer.buffer_sizes["snapshots"] == 2

    await writer.add_snapshot(make_snapshot(seq=3))
    assert writer.buffer_sizes["snapshots"] == 0


async def test_flush_all_processes_all_buffers(writer, mock_pool):
    await writer.add_snapshot(make_snapshot())
    await writer.add_delta(make_delta())
    await writer.add_gap(GapRecord(
        market_ticker="TEST-MKT",
        detected_at=datetime.now(timezone.utc),
        expected_seq=2,
        received_seq=5,
        sid=100,
    ))
    await writer.add_overflow(OverflowRecord(
        market_ticker="OVERFLOW-MKT",
        event_ticker="EVT-1",
    ))
    await writer.add_market_update({
        "ticker": "TEST-MKT",
        "market_id": "id-1",
        "status": "active",
    })

    assert writer.buffer_sizes["snapshots"] == 1
    assert writer.buffer_sizes["deltas"] == 1
    assert writer.buffer_sizes["gaps"] == 1
    assert writer.buffer_sizes["overflow"] == 1
    assert writer.buffer_sizes["markets"] == 1

    await writer.flush_all()

    assert writer.buffer_sizes["snapshots"] == 0
    assert writer.buffer_sizes["deltas"] == 0
    assert writer.buffer_sizes["gaps"] == 0
    assert writer.buffer_sizes["overflow"] == 0
    assert writer.buffer_sizes["markets"] == 0


async def test_buffer_sizes_tracking(writer):
    assert writer.buffer_sizes == {
        "snapshots": 0,
        "deltas": 0,
        "gaps": 0,
        "overflow": 0,
        "markets": 0,
    }

    await writer.add_delta(make_delta(seq=1))
    await writer.add_delta(make_delta(seq=2))
    await writer.add_snapshot(make_snapshot())

    assert writer.buffer_sizes["deltas"] == 2
    assert writer.buffer_sizes["snapshots"] == 1
    assert writer.buffer_sizes["gaps"] == 0
