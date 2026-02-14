"""Tests for orderbook processor."""

from unittest.mock import AsyncMock

import pytest

from src.collector.processor import OrderbookProcessor


@pytest.fixture
def resubscribe_mock():
    return AsyncMock()


@pytest.fixture
def processor(resubscribe_mock):
    proc = OrderbookProcessor(on_resubscribe=resubscribe_mock)
    proc.on_snapshot_ready = AsyncMock()
    proc.on_delta_ready = AsyncMock()
    proc.on_gap_record = AsyncMock()
    return proc


def make_snapshot_msg(ticker="TEST-MKT", seq=1, sid=100):
    return {
        "type": "orderbook_snapshot",
        "sid": sid,
        "seq": seq,
        "msg": {
            "market_ticker": ticker,
            "yes": [[50, 10], [55, 5]],
            "no": [[45, 8]],
            "ts": 1707840000,
        },
    }


def make_delta_msg(ticker="TEST-MKT", seq=2, sid=100, price=50, delta=5, side="yes"):
    return {
        "type": "orderbook_delta",
        "sid": sid,
        "seq": seq,
        "msg": {
            "market_ticker": ticker,
            "price": price,
            "delta": delta,
            "side": side,
            "ts": 1707840001,
        },
    }


async def test_snapshot_sets_tracking_state(processor):
    await processor.handle_snapshot(make_snapshot_msg(seq=1, sid=100))
    sub = processor.get_subscription("TEST-MKT")
    assert sub is not None
    assert sub.last_seq == 1
    assert sub.sid == 100
    assert sub.is_stale is False
    processor.on_snapshot_ready.assert_awaited_once()


async def test_delta_valid_sequence(processor):
    await processor.handle_snapshot(make_snapshot_msg(seq=1, sid=100))
    await processor.handle_delta(make_delta_msg(seq=2, sid=100))
    sub = processor.get_subscription("TEST-MKT")
    assert sub.last_seq == 2
    processor.on_delta_ready.assert_awaited_once()


async def test_delta_gap_detected(processor, resubscribe_mock):
    await processor.handle_snapshot(make_snapshot_msg(seq=1, sid=100))
    # Delta with seq=5 (expected 2) -> GAP
    await processor.handle_delta(make_delta_msg(seq=5, sid=100))
    resubscribe_mock.assert_awaited_once_with("TEST-MKT")
    processor.on_gap_record.assert_awaited_once()
    sub = processor.get_subscription("TEST-MKT")
    assert sub.is_stale is True


async def test_delta_duplicate_discarded(processor):
    await processor.handle_snapshot(make_snapshot_msg(seq=5, sid=100))
    # Delta with seq=3 (< expected 6) -> duplicate
    await processor.handle_delta(make_delta_msg(seq=3, sid=100))
    processor.on_delta_ready.assert_not_awaited()


async def test_gap_recovery_triggers_resubscribe(processor, resubscribe_mock):
    await processor.handle_snapshot(make_snapshot_msg(seq=1, sid=100))
    await processor.handle_delta(make_delta_msg(seq=10, sid=100))
    resubscribe_mock.assert_awaited_once_with("TEST-MKT")


async def test_gap_record_created(processor, resubscribe_mock):
    await processor.handle_snapshot(make_snapshot_msg(seq=1, sid=100))
    await processor.handle_delta(make_delta_msg(seq=5, sid=100))
    gap = processor.on_gap_record.call_args[0][0]
    assert gap.market_ticker == "TEST-MKT"
    assert gap.expected_seq == 2
    assert gap.received_seq == 5


async def test_multiple_markets_independent(processor, resubscribe_mock):
    await processor.handle_snapshot(make_snapshot_msg(ticker="MKT-A", seq=1, sid=10))
    await processor.handle_snapshot(make_snapshot_msg(ticker="MKT-B", seq=1, sid=20))
    # Valid delta for MKT-A
    await processor.handle_delta(make_delta_msg(ticker="MKT-A", seq=2, sid=10))
    # Gap in MKT-B (seq=5, expected 2)
    await processor.handle_delta(make_delta_msg(ticker="MKT-B", seq=5, sid=20))
    # MKT-A should be fine
    assert processor.get_subscription("MKT-A").is_stale is False
    assert processor.get_subscription("MKT-A").last_seq == 2
    # MKT-B should be stale
    assert processor.get_subscription("MKT-B").is_stale is True
    resubscribe_mock.assert_awaited_once_with("MKT-B")


async def test_snapshot_resets_stale(processor, resubscribe_mock):
    await processor.handle_snapshot(make_snapshot_msg(seq=1, sid=100))
    await processor.handle_delta(make_delta_msg(seq=5, sid=100))  # Gap
    assert processor.get_subscription("TEST-MKT").is_stale is True
    # New snapshot resets stale
    await processor.handle_snapshot(make_snapshot_msg(seq=10, sid=200))
    assert processor.get_subscription("TEST-MKT").is_stale is False
    assert processor.get_subscription("TEST-MKT").last_seq == 10
