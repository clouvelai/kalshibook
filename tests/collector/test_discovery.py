"""Tests for market discovery and subscription management."""

from unittest.mock import AsyncMock

import pytest

from src.collector.discovery import MarketDiscovery


@pytest.fixture
def subscribe_mock():
    return AsyncMock()


@pytest.fixture
def unsubscribe_mock():
    return AsyncMock()


@pytest.fixture
def discovery(subscribe_mock, unsubscribe_mock):
    disc = MarketDiscovery(
        max_subscriptions=3,
        subscribe_fn=subscribe_mock,
        unsubscribe_fn=unsubscribe_mock,
    )
    disc.on_market_update = AsyncMock()
    disc.on_overflow_record = AsyncMock()
    return disc


def make_lifecycle_msg(ticker, event_type):
    return {
        "type": "market_lifecycle_v2",
        "sid": 1,
        "seq": 0,
        "msg": {
            "market_ticker": ticker,
            "event_type": event_type,
        },
    }


async def test_new_market_subscribes(discovery, subscribe_mock):
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "created"))
    subscribe_mock.assert_awaited_once_with(["MKT-A"])


async def test_settled_market_unsubscribes(discovery, subscribe_mock, unsubscribe_mock):
    # First subscribe
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "created"))
    discovery.confirm_subscription("MKT-A")
    assert discovery.active_count == 1

    # Then determine (terminal)
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "determined"))
    unsubscribe_mock.assert_awaited_once_with(["MKT-A"])
    assert discovery.active_count == 0


async def test_already_subscribed_skipped(discovery, subscribe_mock):
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "created"))
    subscribe_mock.assert_awaited_once()
    # Same event again should not trigger another subscribe
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "created"))
    subscribe_mock.assert_awaited_once()  # Still only once


async def test_subscription_cap_overflow(discovery, subscribe_mock):
    # Fill up to max_subscriptions=3
    for i in range(3):
        ticker = f"MKT-{i}"
        await discovery.handle_lifecycle_event(make_lifecycle_msg(ticker, "created"))
        discovery.confirm_subscription(ticker)

    assert discovery.active_count == 3
    assert discovery.at_capacity is True

    # Next market should overflow
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-OVERFLOW", "created"))
    assert subscribe_mock.await_count == 3  # Only the original 3
    discovery.on_overflow_record.assert_awaited_once()
    overflow = discovery.on_overflow_record.call_args[0][0]
    assert overflow.market_ticker == "MKT-OVERFLOW"


async def test_overflow_backfill(discovery, subscribe_mock, unsubscribe_mock):
    # Fill to capacity
    for i in range(3):
        ticker = f"MKT-{i}"
        await discovery.handle_lifecycle_event(make_lifecycle_msg(ticker, "created"))
        discovery.confirm_subscription(ticker)

    # Add overflow market
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-OVERFLOW", "created"))
    assert subscribe_mock.await_count == 3

    # Settle one active market to free a slot
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-0", "determined"))
    # Overflow market should now be subscribed via backfill
    assert subscribe_mock.await_count == 4
    last_call_args = subscribe_mock.call_args_list[-1][0][0]
    assert last_call_args == ["MKT-OVERFLOW"]


async def test_resubscribe_list(discovery):
    # Add some active and pending subscriptions
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "created"))
    discovery.confirm_subscription("MKT-A")
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-B", "created"))
    # MKT-B is pending (not confirmed)

    resub_list = discovery.get_resubscribe_list()
    assert set(resub_list) == {"MKT-A", "MKT-B"}


async def test_confirm_subscription(discovery):
    await discovery.handle_lifecycle_event(make_lifecycle_msg("MKT-A", "created"))
    # Before confirmation: pending but not active
    assert discovery.active_count == 0

    discovery.confirm_subscription("MKT-A")
    assert discovery.active_count == 1
