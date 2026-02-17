"""Tests for KalshiBook endpoint methods (sync and async) using pytest-httpx mocks."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from kalshibook import KalshiBook, MarketNotFoundError, ValidationError

# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

BASE_URL = "https://api.kalshibook.io"

CREDIT_HEADERS = {"x-credits-cost": "1", "x-credits-remaining": "999"}
CREDIT_HEADERS_5 = {"x-credits-cost": "5", "x-credits-remaining": "995"}

TIMESTAMP_ISO = "2026-01-15T12:00:00+00:00"
SNAPSHOT_BASIS_ISO = "2026-01-15T11:55:00+00:00"
DISCOVERED_AT_ISO = "2025-06-01T00:00:00+00:00"
BUCKET_ISO = "2026-01-15T12:00:00+00:00"


# ---------------------------------------------------------------------------
# Sync happy-path tests
# ---------------------------------------------------------------------------


def test_get_orderbook(httpx_mock):
    """Sync get_orderbook returns OrderbookResponse with correct fields."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/orderbook",
        method="POST",
        json={
            "market_ticker": "KXBTC-TEST",
            "timestamp": TIMESTAMP_ISO,
            "snapshot_basis": SNAPSHOT_BASIS_ISO,
            "deltas_applied": 42,
            "yes": [
                {"price": 55, "quantity": 100},
                {"price": 54, "quantity": 200},
            ],
            "no": [
                {"price": 45, "quantity": 150},
            ],
            "request_id": "req_ob_1",
            "response_time": 0.05,
        },
        headers=CREDIT_HEADERS_5,
    )

    client = KalshiBook("kb-test-key")
    result = client.get_orderbook("KXBTC-TEST", datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc))

    assert result.market_ticker == "KXBTC-TEST"
    assert len(result.yes) == 2
    assert len(result.no) == 1
    assert result.yes[0].price == 55
    assert result.yes[0].quantity == 100
    assert result.deltas_applied == 42
    assert result.meta.credits_used == 5
    assert result.meta.credits_remaining == 995
    assert result.meta.request_id == "req_ob_1"
    client.close()


def test_list_markets(httpx_mock):
    """Sync list_markets returns MarketsResponse with list of MarketSummary."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/markets",
        method="GET",
        json={
            "data": [
                {
                    "ticker": "MKT-1",
                    "status": "active",
                    "title": "Test Market",
                    "event_ticker": "EVT-1",
                    "category": "Crypto",
                    "first_data_at": TIMESTAMP_ISO,
                    "last_data_at": TIMESTAMP_ISO,
                },
            ],
            "request_id": "req_lm_1",
            "response_time": 0.02,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.list_markets()

    assert len(result.data) == 1
    assert result.data[0].ticker == "MKT-1"
    assert result.data[0].status == "active"
    assert result.meta.credits_used == 1
    client.close()


def test_get_market(httpx_mock):
    """Sync get_market returns MarketDetailResponse with nested MarketDetail."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/markets/KXBTC-TEST",
        method="GET",
        json={
            "data": {
                "ticker": "KXBTC-TEST",
                "status": "active",
                "title": "Bitcoin Test",
                "event_ticker": "KXBTC",
                "category": "Crypto",
                "first_data_at": TIMESTAMP_ISO,
                "last_data_at": TIMESTAMP_ISO,
                "rules": "Standard rules",
                "strike_price": 50000.0,
                "discovered_at": DISCOVERED_AT_ISO,
                "metadata": {"key": "value"},
                "snapshot_count": 100,
                "delta_count": 5000,
            },
            "request_id": "req_gm_1",
            "response_time": 0.03,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.get_market("KXBTC-TEST")

    assert result.data.ticker == "KXBTC-TEST"
    assert result.data.snapshot_count == 100
    assert result.data.delta_count == 5000
    assert result.data.strike_price == 50000.0
    assert result.meta.credits_used == 1
    client.close()


def test_get_candles(httpx_mock):
    """Sync get_candles returns CandlesResponse with CandleRecord list."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/candles/KXBTC-TEST",
        method="GET",
        match_params={
            "start_time": "2026-01-15T00:00:00+00:00",
            "end_time": "2026-01-16T00:00:00+00:00",
            "interval": "1h",
        },
        json={
            "data": [
                {
                    "bucket": BUCKET_ISO,
                    "market_ticker": "KXBTC-TEST",
                    "open": 55,
                    "high": 60,
                    "low": 50,
                    "close": 58,
                    "volume": 1000,
                    "trade_count": 42,
                },
            ],
            "request_id": "req_gc_1",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.get_candles(
        "KXBTC-TEST",
        start_time=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc),
        interval="1h",
    )

    assert len(result.data) == 1
    assert result.data[0].open == 55
    assert result.data[0].market_ticker == "KXBTC-TEST"
    assert result.data[0].high == 60
    assert result.data[0].volume == 1000
    assert result.meta.credits_used == 1
    client.close()


def test_list_events(httpx_mock):
    """Sync list_events returns EventsResponse with EventSummary list."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/events",
        method="GET",
        json={
            "data": [
                {
                    "event_ticker": "KXBTC",
                    "series_ticker": "KXBTC-SERIES",
                    "title": "Bitcoin Event",
                    "sub_title": "Weekly",
                    "category": "Crypto",
                    "mutually_exclusive": True,
                    "status": "open",
                    "market_count": 5,
                },
            ],
            "request_id": "req_le_1",
            "response_time": 0.02,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.list_events()

    assert len(result.data) == 1
    assert result.data[0].event_ticker == "KXBTC"
    assert result.data[0].status == "open"
    assert result.data[0].market_count == 5
    assert result.meta.credits_used == 1
    client.close()


def test_get_event(httpx_mock):
    """Sync get_event returns EventDetailResponse with nested markets list."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/events/KXBTC",
        method="GET",
        json={
            "data": {
                "event_ticker": "KXBTC",
                "series_ticker": "KXBTC-SERIES",
                "title": "Bitcoin Event",
                "sub_title": "Weekly",
                "category": "Crypto",
                "mutually_exclusive": True,
                "status": "open",
                "market_count": 2,
                "markets": [
                    {
                        "ticker": "KXBTC-T50",
                        "status": "active",
                        "title": "BTC > 50k",
                        "event_ticker": "KXBTC",
                        "category": "Crypto",
                        "first_data_at": TIMESTAMP_ISO,
                        "last_data_at": TIMESTAMP_ISO,
                    },
                    {
                        "ticker": "KXBTC-T60",
                        "status": "active",
                        "title": "BTC > 60k",
                        "event_ticker": "KXBTC",
                        "category": "Crypto",
                        "first_data_at": TIMESTAMP_ISO,
                        "last_data_at": TIMESTAMP_ISO,
                    },
                ],
            },
            "request_id": "req_ge_1",
            "response_time": 0.04,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.get_event("KXBTC")

    assert result.data.event_ticker == "KXBTC"
    assert len(result.data.markets) == 2
    assert result.data.markets[0].ticker == "KXBTC-T50"
    assert result.data.markets[1].ticker == "KXBTC-T60"
    assert result.meta.credits_used == 1
    client.close()


# ---------------------------------------------------------------------------
# ResponseMeta extraction test
# ---------------------------------------------------------------------------


def test_response_meta_extracted(httpx_mock):
    """ResponseMeta credits_used and credits_remaining are extracted from headers."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/markets",
        method="GET",
        json={
            "data": [],
            "request_id": "req_test",
            "response_time": 0.001,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.list_markets()

    assert result.meta.credits_used == 1
    assert result.meta.credits_remaining == 999
    assert result.meta.request_id == "req_test"
    assert result.meta.response_time == pytest.approx(0.001)
    client.close()


# ---------------------------------------------------------------------------
# Error mapping tests
# ---------------------------------------------------------------------------


def test_market_not_found_raises(httpx_mock):
    """404 with market_not_found code raises MarketNotFoundError."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/markets/NONEXISTENT",
        method="GET",
        status_code=404,
        json={
            "error": {
                "code": "market_not_found",
                "message": "Market NONEXISTENT not found",
            },
        },
    )

    client = KalshiBook("kb-test-key")
    with pytest.raises(MarketNotFoundError) as exc_info:
        client.get_market("NONEXISTENT")

    assert exc_info.value.status_code == 404
    assert "NONEXISTENT" in exc_info.value.message
    client.close()


def test_validation_error_raises(httpx_mock):
    """422 with validation_error code raises ValidationError."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/orderbook",
        method="POST",
        status_code=422,
        json={
            "error": {
                "code": "validation_error",
                "message": "Invalid timestamp format",
            },
        },
    )

    client = KalshiBook("kb-test-key")
    with pytest.raises(ValidationError) as exc_info:
        client.get_orderbook(
            "KXBTC-TEST",
            datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        )

    assert exc_info.value.status_code == 422
    client.close()


# ---------------------------------------------------------------------------
# Naive datetime UTC handling test
# ---------------------------------------------------------------------------


def test_naive_datetime_gets_utc(httpx_mock):
    """Naive datetime is converted to UTC before sending to API."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/orderbook",
        method="POST",
        json={
            "market_ticker": "KXBTC-TEST",
            "timestamp": TIMESTAMP_ISO,
            "snapshot_basis": SNAPSHOT_BASIS_ISO,
            "deltas_applied": 0,
            "yes": [],
            "no": [],
            "request_id": "req_tz",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS_5,
    )

    client = KalshiBook("kb-test-key")
    # Pass a naive datetime (no tzinfo)
    client.get_orderbook("KXBTC-TEST", datetime(2026, 1, 1, 12, 0))

    request = httpx_mock.get_request()
    body = json.loads(request.content)
    # The timestamp should have been converted to UTC (+00:00)
    assert "+00:00" in body["timestamp"]
    client.close()


# ---------------------------------------------------------------------------
# Optional filter params test
# ---------------------------------------------------------------------------


def test_list_events_filters(httpx_mock):
    """Optional filter params are included when set and excluded when None."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/events",
        method="GET",
        match_params={"category": "Crypto", "status": "active"},
        json={
            "data": [],
            "request_id": "req_filt",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    client.list_events(category="Crypto", status="active")

    request = httpx_mock.get_request()
    params = dict(request.url.params)
    assert params["category"] == "Crypto"
    assert params["status"] == "active"
    assert "series_ticker" not in params
    client.close()


# ---------------------------------------------------------------------------
# Async endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aget_orderbook(httpx_mock):
    """Async aget_orderbook returns OrderbookResponse with correct fields."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/orderbook",
        method="POST",
        json={
            "market_ticker": "KXBTC-TEST",
            "timestamp": TIMESTAMP_ISO,
            "snapshot_basis": SNAPSHOT_BASIS_ISO,
            "deltas_applied": 10,
            "yes": [{"price": 55, "quantity": 100}],
            "no": [{"price": 45, "quantity": 150}],
            "request_id": "req_aob_1",
            "response_time": 0.02,
        },
        headers=CREDIT_HEADERS_5,
    )

    client = KalshiBook("kb-test-key", sync=False)
    result = await client.aget_orderbook(
        "KXBTC-TEST",
        datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )

    assert result.market_ticker == "KXBTC-TEST"
    assert len(result.yes) == 1
    assert result.yes[0].price == 55
    assert result.deltas_applied == 10
    assert result.meta.credits_used == 5
    await client.aclose()


@pytest.mark.asyncio
async def test_aget_market(httpx_mock):
    """Async aget_market returns MarketDetailResponse."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/markets/KXBTC-TEST",
        method="GET",
        json={
            "data": {
                "ticker": "KXBTC-TEST",
                "status": "active",
                "title": "Bitcoin Test",
                "event_ticker": "KXBTC",
                "category": "Crypto",
                "first_data_at": TIMESTAMP_ISO,
                "last_data_at": TIMESTAMP_ISO,
                "rules": None,
                "strike_price": None,
                "discovered_at": DISCOVERED_AT_ISO,
                "metadata": None,
                "snapshot_count": 50,
                "delta_count": 2500,
            },
            "request_id": "req_agm_1",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key", sync=False)
    result = await client.aget_market("KXBTC-TEST")

    assert result.data.ticker == "KXBTC-TEST"
    assert result.data.snapshot_count == 50
    assert result.meta.credits_used == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_alist_events(httpx_mock):
    """Async alist_events returns EventsResponse with EventSummary list."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/events",
        method="GET",
        json={
            "data": [
                {
                    "event_ticker": "KXBTC",
                    "series_ticker": "KXBTC-SERIES",
                    "title": "Bitcoin Event",
                    "sub_title": None,
                    "category": "Crypto",
                    "mutually_exclusive": True,
                    "status": "open",
                    "market_count": 3,
                },
            ],
            "request_id": "req_ale_1",
            "response_time": 0.02,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key", sync=False)
    result = await client.alist_events()

    assert len(result.data) >= 1
    assert result.data[0].event_ticker == "KXBTC"
    assert result.meta.credits_used == 1
    await client.aclose()
