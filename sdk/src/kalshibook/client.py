"""KalshiBook client -- query L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations


class KalshiBook:
    """Client for the KalshiBook API.

    Provides sync and async access to historical orderbook data,
    trades, candles, events, and settlements for Kalshi prediction markets.

    Usage::

        from kalshibook import KalshiBook

        client = KalshiBook(api_key="kb-...")

    Parameters
    ----------
    api_key : str, optional
        KalshiBook API key. If not provided, reads from KALSHIBOOK_API_KEY env var.
    sync : bool, optional
        If True, use synchronous HTTP transport. Default False (async).
    """

    pass
