"""KalshiBook Python SDK -- L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations

__version__ = "0.1.0"

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
    "__version__",
    "KalshiBookError",
    "AuthenticationError",
    "RateLimitError",
    "CreditsExhaustedError",
    "MarketNotFoundError",
    "ValidationError",
]
