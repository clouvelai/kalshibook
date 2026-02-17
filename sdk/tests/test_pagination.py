"""Tests for paginated endpoints, settlements, and DataFrame conversion."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone

import pytest

from kalshibook import KalshiBook, MarketNotFoundError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.kalshibook.io"

CREDIT_HEADERS = {"x-credits-cost": "1", "x-credits-remaining": "999"}

TS = "2026-01-15T12:00:00+00:00"
START = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)

SETTLED_AT = "2026-01-15T18:00:00+00:00"
DETERMINED_AT = "2026-01-15T17:30:00+00:00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _delta_record(seq: int = 1, side: str = "yes") -> dict:
    """Build a single delta record dict."""
    return {
        "market_ticker": "KXBTC-T50",
        "ts": TS,
        "seq": seq,
        "price_cents": 55,
        "delta_amount": 100,
        "side": side,
    }


def _trade_record(trade_id: str = "t1", taker_side: str = "yes") -> dict:
    """Build a single trade record dict."""
    return {
        "trade_id": trade_id,
        "market_ticker": "KXBTC-T50",
        "yes_price": 55,
        "no_price": 45,
        "count": 10,
        "taker_side": taker_side,
        "ts": TS,
    }


def _settlement_record(ticker: str = "KXBTC-T50") -> dict:
    """Build a single settlement record dict."""
    return {
        "market_ticker": ticker,
        "event_ticker": "KXBTC",
        "result": "yes",
        "settlement_value": 100,
        "determined_at": DETERMINED_AT,
        "settled_at": SETTLED_AT,
    }


def _page_response(data: list, *, has_more: bool = False, next_cursor: str | None = None) -> dict:
    """Wrap records in a paginated response envelope."""
    resp: dict = {
        "data": data,
        "has_more": has_more,
        "request_id": "req_pg",
        "response_time": 0.01,
    }
    if next_cursor is not None:
        resp["next_cursor"] = next_cursor
    return resp


# ---------------------------------------------------------------------------
# Pagination tests -- Deltas
# ---------------------------------------------------------------------------


def test_list_deltas_single_page(httpx_mock):
    """Single page of deltas iterates all items."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([_delta_record(seq=1), _delta_record(seq=2)]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    items = list(client.list_deltas("KXBTC-T50", START, END))

    assert len(items) == 2
    assert items[0].seq == 1
    assert items[1].seq == 2
    assert items[0].market_ticker == "KXBTC-T50"
    client.close()


def test_list_deltas_multi_page(httpx_mock):
    """Multi-page deltas are fetched transparently."""
    # Page 1
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response(
            [_delta_record(seq=1)],
            has_more=True,
            next_cursor="cursor_abc",
        ),
        headers=CREDIT_HEADERS,
    )
    # Page 2
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([_delta_record(seq=2)]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    items = list(client.list_deltas("KXBTC-T50", START, END))

    assert len(items) == 2
    assert items[0].seq == 1
    assert items[1].seq == 2
    client.close()


def test_list_deltas_empty(httpx_mock):
    """Empty first page returns no items."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    items = list(client.list_deltas("KXBTC-T50", START, END))

    assert items == []
    client.close()


# ---------------------------------------------------------------------------
# Pagination tests -- Trades
# ---------------------------------------------------------------------------


def test_list_trades_single_page(httpx_mock):
    """Single page of trades iterates all items with correct fields."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/trades",
        method="POST",
        json=_page_response([_trade_record("t1"), _trade_record("t2", taker_side="no")]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    items = list(client.list_trades("KXBTC-T50", START, END))

    assert len(items) == 2
    assert items[0].trade_id == "t1"
    assert items[0].taker_side == "yes"
    assert items[1].trade_id == "t2"
    assert items[1].taker_side == "no"
    assert items[0].yes_price == 55
    assert items[0].no_price == 45
    client.close()


def test_list_trades_multi_page(httpx_mock):
    """Multi-page trades are fetched transparently."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/trades",
        method="POST",
        json=_page_response(
            [_trade_record("t1")],
            has_more=True,
            next_cursor="cursor_xyz",
        ),
        headers=CREDIT_HEADERS,
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}/trades",
        method="POST",
        json=_page_response([_trade_record("t2")]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    items = list(client.list_trades("KXBTC-T50", START, END))

    assert len(items) == 2
    assert items[0].trade_id == "t1"
    assert items[1].trade_id == "t2"
    client.close()


# ---------------------------------------------------------------------------
# Settlement tests
# ---------------------------------------------------------------------------


def test_list_settlements(httpx_mock):
    """list_settlements returns SettlementsResponse with records."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/settlements",
        method="GET",
        json={
            "data": [_settlement_record("KXBTC-T50"), _settlement_record("KXBTC-T60")],
            "request_id": "req_ls",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.list_settlements()

    assert len(result.data) == 2
    assert result.data[0].market_ticker == "KXBTC-T50"
    assert result.data[1].market_ticker == "KXBTC-T60"
    assert result.data[0].result == "yes"
    assert result.meta.credits_used == 1
    client.close()


def test_list_settlements_filters(httpx_mock):
    """Filter params are forwarded as query params."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/settlements",
        method="GET",
        match_params={"event_ticker": "KXBTC", "result": "yes"},
        json={
            "data": [_settlement_record()],
            "request_id": "req_lsf",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.list_settlements(event_ticker="KXBTC", result="yes")

    request = httpx_mock.get_request()
    params = dict(request.url.params)
    assert params["event_ticker"] == "KXBTC"
    assert params["result"] == "yes"
    assert len(result.data) == 1
    client.close()


def test_get_settlement(httpx_mock):
    """get_settlement returns single SettlementResponse."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/settlements/KXBTC-T50",
        method="GET",
        json={
            "data": _settlement_record(),
            "request_id": "req_gs",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    result = client.get_settlement("KXBTC-T50")

    assert result.data.market_ticker == "KXBTC-T50"
    assert result.data.result == "yes"
    assert result.data.settlement_value == 100
    assert result.meta.credits_used == 1
    client.close()


def test_get_settlement_not_found(httpx_mock):
    """404 on settlement raises MarketNotFoundError."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/settlements/NONEXISTENT",
        method="GET",
        status_code=404,
        json={
            "error": {
                "code": "market_not_found",
                "message": "Settlement not found for NONEXISTENT",
            },
        },
    )

    client = KalshiBook("kb-test-key")
    with pytest.raises(MarketNotFoundError) as exc_info:
        client.get_settlement("NONEXISTENT")

    assert exc_info.value.status_code == 404
    assert "NONEXISTENT" in exc_info.value.message
    client.close()


# ---------------------------------------------------------------------------
# DataFrame tests
# ---------------------------------------------------------------------------


def test_page_iterator_to_df(httpx_mock):
    """to_df() returns DataFrame with correct columns and row count."""
    pd = pytest.importorskip("pandas")

    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([_delta_record(seq=1), _delta_record(seq=2)]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    df = client.list_deltas("KXBTC-T50", START, END).to_df()

    assert len(df) == 2
    assert "market_ticker" in df.columns
    assert "seq" in df.columns
    assert "price_cents" in df.columns
    assert list(df["seq"]) == [1, 2]
    client.close()


def test_to_df_after_partial_iteration(httpx_mock):
    """to_df() includes already-iterated items."""
    pd = pytest.importorskip("pandas")

    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([_delta_record(seq=1), _delta_record(seq=2)]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    iterator = client.list_deltas("KXBTC-T50", START, END)

    # Iterate one item
    first = next(iterator)
    assert first.seq == 1

    # to_df should contain ALL items (including the already-consumed one)
    df = iterator.to_df()
    assert len(df) == 2
    assert list(df["seq"]) == [1, 2]
    client.close()


def test_to_df_raises_without_pandas(httpx_mock, monkeypatch):
    """to_df() raises ImportError with install hint when pandas missing."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([_delta_record(seq=1)]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    iterator = client.list_deltas("KXBTC-T50", START, END)

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("No module named 'pandas'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with pytest.raises(ImportError, match=r"kalshibook\[pandas\]"):
        iterator.to_df()

    client.close()


def test_settlements_response_to_df(httpx_mock):
    """SettlementsResponse.to_df() returns DataFrame with settlement columns."""
    pd = pytest.importorskip("pandas")

    httpx_mock.add_response(
        url=f"{BASE_URL}/settlements",
        method="GET",
        json={
            "data": [_settlement_record("KXBTC-T50"), _settlement_record("KXBTC-T60")],
            "request_id": "req_sdf",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    df = client.list_settlements().to_df()

    assert len(df) == 2
    assert "market_ticker" in df.columns
    assert "result" in df.columns
    assert "settlement_value" in df.columns
    client.close()


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alist_deltas(httpx_mock):
    """Async alist_deltas iterates single page."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json=_page_response([_delta_record(seq=1), _delta_record(seq=2)]),
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key", sync=False)
    iterator = await client.alist_deltas("KXBTC-T50", START, END)

    items = []
    async for item in iterator:
        items.append(item)

    assert len(items) == 2
    assert items[0].seq == 1
    assert items[1].seq == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_aget_settlement(httpx_mock):
    """Async aget_settlement returns single record."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/settlements/KXBTC-T50",
        method="GET",
        json={
            "data": _settlement_record(),
            "request_id": "req_ags",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key", sync=False)
    result = await client.aget_settlement("KXBTC-T50")

    assert result.data.market_ticker == "KXBTC-T50"
    assert result.data.result == "yes"
    assert result.meta.credits_used == 1
    await client.aclose()
