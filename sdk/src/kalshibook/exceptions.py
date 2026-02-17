"""Exception hierarchy for KalshiBook SDK errors."""

from __future__ import annotations

from typing import Any


class KalshiBookError(Exception):
    """Base exception for all KalshiBook SDK errors.

    All SDK exceptions carry contextual information about the failed request:

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code from the API response (0 if not applicable).
        response_body: Parsed JSON body from the API error response.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.response_body = response_body if response_body is not None else {}
        super().__init__(message)


class AuthenticationError(KalshiBookError):
    """API key is missing, malformed, or invalid."""


class RateLimitError(KalshiBookError):
    """Request was rate-limited (HTTP 429, code=rate_limit_exceeded).

    The SDK auto-retries these transparently. If you see this exception,
    all retry attempts were exhausted.
    """


class CreditsExhaustedError(KalshiBookError):
    """Monthly credit limit reached (HTTP 429, code=credits_exhausted).

    Not retryable. Enable Pay-As-You-Go or upgrade plan.
    """


class MarketNotFoundError(KalshiBookError):
    """The requested market, event, or settlement was not found (HTTP 404)."""


class ValidationError(KalshiBookError):
    """Request validation failed (HTTP 422)."""
