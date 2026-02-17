"""KalshiBook Python SDK -- L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations

from kalshibook._version import __version__

from kalshibook._pagination import PageIterator
from kalshibook.client import KalshiBook
from kalshibook.exceptions import (
    AuthenticationError,
    CreditsExhaustedError,
    KalshiBookError,
    MarketNotFoundError,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "KalshiBook",
    "PageIterator",
    "__version__",
    "KalshiBookError",
    "AuthenticationError",
    "RateLimitError",
    "CreditsExhaustedError",
    "MarketNotFoundError",
    "ValidationError",
]
