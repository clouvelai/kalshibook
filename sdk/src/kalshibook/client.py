"""KalshiBook client -- query L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from kalshibook._http import HttpTransport
from kalshibook._pagination import PageIterator
from kalshibook.exceptions import AuthenticationError
from kalshibook.models import (
    CandlesResponse,
    DeltaRecord,
    DeltasResponse,
    EventDetailResponse,
    EventsResponse,
    MarketDetailResponse,
    MarketsResponse,
    OrderbookResponse,
    ResponseMeta,
    SettlementResponse,
    SettlementsResponse,
    TradeRecord,
    TradesResponse,
)


class KalshiBook:
    """Client for the KalshiBook API.

    Provides sync and async access to historical orderbook data,
    trades, candles, events, and settlements for Kalshi prediction markets.

    Usage::

        # Sync (default -- scripts and notebooks)
        client = KalshiBook("kb-your-api-key")

        # From environment variable
        client = KalshiBook.from_env()

        # Async
        client = KalshiBook("kb-your-api-key", sync=False)

        # Context manager
        with KalshiBook("kb-your-api-key") as client:
            ...

    Parameters
    ----------
    api_key : str, optional
        KalshiBook API key (must start with 'kb-'). If not provided,
        reads from KALSHIBOOK_API_KEY environment variable.
    base_url : str, optional
        API base URL. Default: https://api.kalshibook.io
    sync : bool, optional
        If True (default), use synchronous HTTP transport.
        Set to False for async usage in event loop contexts.
    timeout : float, optional
        Request timeout in seconds. Default: 30.0
    max_retries : int, optional
        Maximum retry attempts for rate-limited requests. Default: 3
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.kalshibook.io",
        sync: bool = True,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        resolved_key = api_key or os.environ.get("KALSHIBOOK_API_KEY", "")

        if not resolved_key:
            raise AuthenticationError(
                message=(
                    "No API key provided. Pass api_key= or set "
                    "KALSHIBOOK_API_KEY environment variable."
                ),
                status_code=0,
                response_body={},
            )

        if not resolved_key.startswith("kb-"):
            raise AuthenticationError(
                message=(
                    f"Invalid API key format. Keys must start with "
                    f"'kb-', got '{resolved_key[:10]}...'"
                ),
                status_code=0,
                response_body={},
            )

        self._transport = HttpTransport(
            api_key=resolved_key,
            base_url=base_url,
            sync=sync,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._sync = sync

    @classmethod
    def from_env(cls, **kwargs: Any) -> KalshiBook:
        """Create client using KALSHIBOOK_API_KEY environment variable."""
        return cls(api_key=None, **kwargs)

    # -- Context manager support (sync and async) --

    def __enter__(self) -> KalshiBook:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> KalshiBook:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    # -- Cleanup --

    def close(self) -> None:
        """Close the underlying HTTP transport (sync)."""
        self._transport.close()

    async def aclose(self) -> None:
        """Close the underlying HTTP transport (async)."""
        await self._transport.aclose()

    # -- Private helpers --

    def _ensure_tz(self, dt: datetime) -> datetime:
        """Return *dt* with UTC tzinfo if it is naive, otherwise unchanged."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Dispatch a synchronous HTTP request via the transport layer."""
        return self._transport.request_sync(method, path, **kwargs)

    async def _arequest(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Dispatch an asynchronous HTTP request via the transport layer."""
        return await self._transport.request_async(method, path, **kwargs)

    def _parse_response(self, resp: httpx.Response, model_cls: type) -> Any:
        """Deserialise *resp* into *model_cls* with :class:`ResponseMeta`."""
        body = resp.json()
        meta = ResponseMeta.from_headers(dict(resp.headers), body)
        return model_cls.from_dict(body, meta)

    # -- Orderbook --

    def get_orderbook(
        self,
        ticker: str,
        timestamp: datetime,
        *,
        depth: int | None = None,
    ) -> OrderbookResponse:
        """Reconstruct the L2 orderbook for *ticker* at *timestamp*.

        Parameters
        ----------
        ticker : str
            Market ticker (e.g. ``"KXBTC-24MAR14-T50000"``).
        timestamp : datetime
            Point-in-time for the reconstruction.  Timezone-aware recommended;
            naive datetimes are assumed UTC.
        depth : int, optional
            Max price levels per side.  ``None`` returns all levels.

        Returns
        -------
        OrderbookResponse

        Raises
        ------
        MarketNotFoundError
            If the ticker does not exist or has no data at *timestamp*.
        ValidationError
            If the timestamp or depth value is invalid.
        """
        body: dict[str, Any] = {
            "market_ticker": ticker,
            "timestamp": self._ensure_tz(timestamp).isoformat(),
        }
        if depth is not None:
            body["depth"] = depth
        resp = self._request("POST", "/orderbook", json=body)
        return self._parse_response(resp, OrderbookResponse)

    async def aget_orderbook(
        self,
        ticker: str,
        timestamp: datetime,
        *,
        depth: int | None = None,
    ) -> OrderbookResponse:
        """Async version of :meth:`get_orderbook`."""
        body: dict[str, Any] = {
            "market_ticker": ticker,
            "timestamp": self._ensure_tz(timestamp).isoformat(),
        }
        if depth is not None:
            body["depth"] = depth
        resp = await self._arequest("POST", "/orderbook", json=body)
        return self._parse_response(resp, OrderbookResponse)

    # -- Markets --

    def list_markets(self) -> MarketsResponse:
        """List all available markets.

        Returns
        -------
        MarketsResponse
            Contains a list of :class:`MarketSummary` items.
        """
        resp = self._request("GET", "/markets")
        return self._parse_response(resp, MarketsResponse)

    async def alist_markets(self) -> MarketsResponse:
        """Async version of :meth:`list_markets`."""
        resp = await self._arequest("GET", "/markets")
        return self._parse_response(resp, MarketsResponse)

    def get_market(self, ticker: str) -> MarketDetailResponse:
        """Get full detail for a single market.

        Parameters
        ----------
        ticker : str
            Market ticker.

        Returns
        -------
        MarketDetailResponse

        Raises
        ------
        MarketNotFoundError
            If the ticker does not exist.
        """
        resp = self._request("GET", f"/markets/{ticker}")
        return self._parse_response(resp, MarketDetailResponse)

    async def aget_market(self, ticker: str) -> MarketDetailResponse:
        """Async version of :meth:`get_market`."""
        resp = await self._arequest("GET", f"/markets/{ticker}")
        return self._parse_response(resp, MarketDetailResponse)

    # -- Candles --

    def get_candles(
        self,
        ticker: str,
        *,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h",
    ) -> CandlesResponse:
        """Get OHLCV candles for *ticker* within a time range.

        Parameters
        ----------
        ticker : str
            Market ticker.
        start_time : datetime
            Beginning of the range (inclusive).  Naive datetimes assumed UTC.
        end_time : datetime
            End of the range (exclusive).  Naive datetimes assumed UTC.
        interval : str
            Candle width.  Common values: ``"1m"``, ``"1h"``, ``"1d"``.
            Server validates for forward-compatibility.

        Returns
        -------
        CandlesResponse
        """
        params = {
            "start_time": self._ensure_tz(start_time).isoformat(),
            "end_time": self._ensure_tz(end_time).isoformat(),
            "interval": interval,
        }
        resp = self._request("GET", f"/candles/{ticker}", params=params)
        return self._parse_response(resp, CandlesResponse)

    async def aget_candles(
        self,
        ticker: str,
        *,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h",
    ) -> CandlesResponse:
        """Async version of :meth:`get_candles`."""
        params = {
            "start_time": self._ensure_tz(start_time).isoformat(),
            "end_time": self._ensure_tz(end_time).isoformat(),
            "interval": interval,
        }
        resp = await self._arequest("GET", f"/candles/{ticker}", params=params)
        return self._parse_response(resp, CandlesResponse)

    # -- Events --

    def list_events(
        self,
        *,
        category: str | None = None,
        series_ticker: str | None = None,
        status: str | None = None,
    ) -> EventsResponse:
        """List events with optional filters.

        Parameters
        ----------
        category : str, optional
            Filter by category slug.
        series_ticker : str, optional
            Filter by parent series ticker.
        status : str, optional
            Filter by event status (e.g. ``"open"``, ``"closed"``).

        Returns
        -------
        EventsResponse
        """
        params: dict[str, str] = {}
        if category is not None:
            params["category"] = category
        if series_ticker is not None:
            params["series_ticker"] = series_ticker
        if status is not None:
            params["status"] = status
        resp = self._request("GET", "/events", params=params or None)
        return self._parse_response(resp, EventsResponse)

    async def alist_events(
        self,
        *,
        category: str | None = None,
        series_ticker: str | None = None,
        status: str | None = None,
    ) -> EventsResponse:
        """Async version of :meth:`list_events`."""
        params: dict[str, str] = {}
        if category is not None:
            params["category"] = category
        if series_ticker is not None:
            params["series_ticker"] = series_ticker
        if status is not None:
            params["status"] = status
        resp = await self._arequest("GET", "/events", params=params or None)
        return self._parse_response(resp, EventsResponse)

    def get_event(self, event_ticker: str) -> EventDetailResponse:
        """Get full detail for a single event, including child markets.

        Parameters
        ----------
        event_ticker : str
            Event ticker.

        Returns
        -------
        EventDetailResponse

        Raises
        ------
        MarketNotFoundError
            If the event ticker does not exist.
        """
        resp = self._request("GET", f"/events/{event_ticker}")
        return self._parse_response(resp, EventDetailResponse)

    async def aget_event(self, event_ticker: str) -> EventDetailResponse:
        """Async version of :meth:`get_event`."""
        resp = await self._arequest("GET", f"/events/{event_ticker}")
        return self._parse_response(resp, EventDetailResponse)

    # -- Settlements --

    def list_settlements(
        self,
        *,
        event_ticker: str | None = None,
        result: str | None = None,
    ) -> SettlementsResponse:
        """List settlement results with optional filters.

        Parameters
        ----------
        event_ticker : str, optional
            Filter by parent event ticker.
        result : str, optional
            Filter by settlement result (e.g. ``"yes"``, ``"no"``).

        Returns
        -------
        SettlementsResponse
        """
        params: dict[str, str] = {}
        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        if result is not None:
            params["result"] = result
        resp = self._request("GET", "/settlements", params=params or None)
        return self._parse_response(resp, SettlementsResponse)

    async def alist_settlements(
        self,
        *,
        event_ticker: str | None = None,
        result: str | None = None,
    ) -> SettlementsResponse:
        """Async version of :meth:`list_settlements`."""
        params: dict[str, str] = {}
        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        if result is not None:
            params["result"] = result
        resp = await self._arequest("GET", "/settlements", params=params or None)
        return self._parse_response(resp, SettlementsResponse)

    def get_settlement(self, ticker: str) -> SettlementResponse:
        """Get settlement result for a single market.

        Parameters
        ----------
        ticker : str
            Market ticker.

        Returns
        -------
        SettlementResponse

        Raises
        ------
        MarketNotFoundError
            If the ticker does not exist or has no settlement.
        """
        resp = self._request("GET", f"/settlements/{ticker}")
        return self._parse_response(resp, SettlementResponse)

    async def aget_settlement(self, ticker: str) -> SettlementResponse:
        """Async version of :meth:`get_settlement`."""
        resp = await self._arequest("GET", f"/settlements/{ticker}")
        return self._parse_response(resp, SettlementResponse)

    # -- Deltas (paginated) --

    def list_deltas(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int = 100,
    ) -> PageIterator[DeltaRecord]:
        """Iterate orderbook deltas for *ticker* within a time range.

        Returns a :class:`PageIterator` that transparently fetches subsequent
        pages on demand.  The first page is fetched eagerly so errors surface
        at call time rather than during iteration.

        Parameters
        ----------
        ticker : str
            Market ticker.
        start_time : datetime
            Beginning of the range (inclusive).  Naive datetimes assumed UTC.
        end_time : datetime
            End of the range (exclusive).  Naive datetimes assumed UTC.
        limit : int, optional
            Page size.  Default: 100.

        Returns
        -------
        PageIterator[DeltaRecord]

        Examples
        --------
        Iterate all deltas::

            for delta in client.list_deltas("KXBTC-T50", start, end):
                print(delta.price_cents, delta.delta_amount)

        Convert to DataFrame::

            df = client.list_deltas("KXBTC-T50", start, end).to_df()
        """
        st = self._ensure_tz(start_time).isoformat()
        et = self._ensure_tz(end_time).isoformat()

        def fetch_page(
            cursor: str | None,
        ) -> tuple[list[DeltaRecord], bool, str | None]:
            body: dict[str, Any] = {
                "market_ticker": ticker,
                "start_time": st,
                "end_time": et,
                "limit": limit,
            }
            if cursor is not None:
                body["cursor"] = cursor
            resp = self._request("POST", "/deltas", json=body)
            parsed = self._parse_response(resp, DeltasResponse)
            return (parsed.data, parsed.has_more, parsed.next_cursor)

        items, has_more, next_cursor = fetch_page(None)
        return PageIterator(items, has_more, next_cursor, fetch_page=fetch_page)

    async def alist_deltas(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int = 100,
    ) -> PageIterator[DeltaRecord]:
        """Async version of :meth:`list_deltas`."""
        st = self._ensure_tz(start_time).isoformat()
        et = self._ensure_tz(end_time).isoformat()

        async def afetch_page(
            cursor: str | None,
        ) -> tuple[list[DeltaRecord], bool, str | None]:
            body: dict[str, Any] = {
                "market_ticker": ticker,
                "start_time": st,
                "end_time": et,
                "limit": limit,
            }
            if cursor is not None:
                body["cursor"] = cursor
            resp = await self._arequest("POST", "/deltas", json=body)
            parsed = self._parse_response(resp, DeltasResponse)
            return (parsed.data, parsed.has_more, parsed.next_cursor)

        items, has_more, next_cursor = await afetch_page(None)
        return PageIterator(items, has_more, next_cursor, afetch_page=afetch_page)

    # -- Trades (paginated) --

    def list_trades(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int = 100,
    ) -> PageIterator[TradeRecord]:
        """Iterate trades for *ticker* within a time range.

        Returns a :class:`PageIterator` that transparently fetches subsequent
        pages on demand.  The first page is fetched eagerly so errors surface
        at call time rather than during iteration.

        Parameters
        ----------
        ticker : str
            Market ticker.
        start_time : datetime
            Beginning of the range (inclusive).  Naive datetimes assumed UTC.
        end_time : datetime
            End of the range (exclusive).  Naive datetimes assumed UTC.
        limit : int, optional
            Page size.  Default: 100.

        Returns
        -------
        PageIterator[TradeRecord]

        Examples
        --------
        Iterate all trades::

            for trade in client.list_trades("KXBTC-T50", start, end):
                print(trade.yes_price, trade.taker_side)

        Convert to DataFrame::

            df = client.list_trades("KXBTC-T50", start, end).to_df()
        """
        st = self._ensure_tz(start_time).isoformat()
        et = self._ensure_tz(end_time).isoformat()

        def fetch_page(
            cursor: str | None,
        ) -> tuple[list[TradeRecord], bool, str | None]:
            body: dict[str, Any] = {
                "market_ticker": ticker,
                "start_time": st,
                "end_time": et,
                "limit": limit,
            }
            if cursor is not None:
                body["cursor"] = cursor
            resp = self._request("POST", "/trades", json=body)
            parsed = self._parse_response(resp, TradesResponse)
            return (parsed.data, parsed.has_more, parsed.next_cursor)

        items, has_more, next_cursor = fetch_page(None)
        return PageIterator(items, has_more, next_cursor, fetch_page=fetch_page)

    async def alist_trades(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
        *,
        limit: int = 100,
    ) -> PageIterator[TradeRecord]:
        """Async version of :meth:`list_trades`."""
        st = self._ensure_tz(start_time).isoformat()
        et = self._ensure_tz(end_time).isoformat()

        async def afetch_page(
            cursor: str | None,
        ) -> tuple[list[TradeRecord], bool, str | None]:
            body: dict[str, Any] = {
                "market_ticker": ticker,
                "start_time": st,
                "end_time": et,
                "limit": limit,
            }
            if cursor is not None:
                body["cursor"] = cursor
            resp = await self._arequest("POST", "/trades", json=body)
            parsed = self._parse_response(resp, TradesResponse)
            return (parsed.data, parsed.has_more, parsed.next_cursor)

        items, has_more, next_cursor = await afetch_page(None)
        return PageIterator(items, has_more, next_cursor, afetch_page=afetch_page)
