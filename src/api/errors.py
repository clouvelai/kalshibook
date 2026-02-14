"""Structured error handling for the KalshiBook API.

All errors return a consistent JSON envelope:
{
    "error": {"code": "...", "message": "...", "status": N},
    "request_id": "req_..."
}
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = structlog.get_logger("api.errors")


# ---------------------------------------------------------------------------
# Request ID generation
# ---------------------------------------------------------------------------

def generate_request_id() -> str:
    """Generate a short request ID for tracing."""
    return f"req_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------

class KalshiBookError(Exception):
    """Base exception for all KalshiBook API errors."""

    def __init__(self, code: str, message: str, status: int) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


# ---------------------------------------------------------------------------
# Specific errors
# ---------------------------------------------------------------------------

class InvalidApiKeyError(KalshiBookError):
    """Raised when the API key is missing, malformed, or revoked."""

    def __init__(self, message: str = "The provided API key is invalid or has been revoked."):
        super().__init__(code="invalid_api_key", message=message, status=401)


class RateLimitExceededError(KalshiBookError):
    """Raised when the client exceeds their rate limit."""

    def __init__(self, message: str = "Rate limit exceeded. Please slow down."):
        super().__init__(code="rate_limit_exceeded", message=message, status=429)


class MarketNotFoundError(KalshiBookError):
    """Raised when the requested market does not exist."""

    def __init__(self, ticker: str = ""):
        msg = f"Market '{ticker}' not found." if ticker else "Market not found."
        super().__init__(code="market_not_found", message=msg, status=404)


class NoDataAvailableError(KalshiBookError):
    """Raised when no data exists for the requested time range."""

    def __init__(self, message: str = "No data available for the requested time range."):
        super().__init__(code="no_data_available", message=message, status=404)


class InvalidTimestampError(KalshiBookError):
    """Raised when the provided timestamp is invalid or out of range."""

    def __init__(self, message: str = "The provided timestamp is invalid or out of range."):
        super().__init__(code="invalid_timestamp", message=message, status=400)


class ValidationError(KalshiBookError):
    """Raised for custom validation failures beyond Pydantic's built-in checks."""

    def __init__(self, message: str = "Validation error."):
        super().__init__(code="validation_error", message=message, status=422)


# ---------------------------------------------------------------------------
# Error response builder
# ---------------------------------------------------------------------------

def _error_response(request: Request, code: str, message: str, status: int) -> JSONResponse:
    """Build a structured error JSON response."""
    request_id = getattr(request.state, "request_id", generate_request_id())
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "status": status,
            },
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

async def _handle_kalshibook_error(request: Request, exc: KalshiBookError) -> JSONResponse:
    """Handle KalshiBookError and subclasses."""
    logger.warning(
        "api_error",
        code=exc.code,
        status=exc.status,
        message=exc.message,
        request_id=getattr(request.state, "request_id", None),
    )
    return _error_response(request, exc.code, exc.message, exc.status)


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors."""
    errors = exc.errors()
    message = "; ".join(
        f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', 'invalid')}"
        for e in errors
    )
    logger.warning(
        "validation_error",
        errors=errors,
        request_id=getattr(request.state, "request_id", None),
    )
    return _error_response(request, "validation_error", message, 422)


async def _handle_rate_limit_exceeded(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Handle SlowAPI rate limit exceeded errors."""
    response = _error_response(
        request,
        "rate_limit_exceeded",
        "Rate limit exceeded. Please retry after the indicated time.",
        429,
    )
    # Include Retry-After header if available
    retry_after = getattr(exc, "detail", None)
    if retry_after:
        response.headers["Retry-After"] = str(retry_after)
    return response


async def _handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with a generic 500 response."""
    logger.error(
        "internal_error",
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=getattr(request.state, "request_id", None),
        exc_info=True,
    )
    return _error_response(
        request,
        "internal_error",
        "An unexpected error occurred. Please try again later.",
        500,
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_exception_handlers(app) -> None:
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(KalshiBookError, _handle_kalshibook_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit_exceeded)
    app.add_exception_handler(Exception, _handle_generic_exception)
