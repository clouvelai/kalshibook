# Phase 9: Models, Exceptions, and HTTP Transport - Research

**Researched:** 2026-02-17
**Domain:** Python SDK internals -- stdlib dataclasses, httpx dual-mode transport, exception hierarchy, credit tracking
**Confidence:** HIGH

## Summary

Phase 9 fills the empty SDK stubs from Phase 8 (`client.py`, `models.py`, `exceptions.py`, `_http.py`) with working implementations. The core challenge is building a single `KalshiBook` class that transparently switches between `httpx.Client` (sync) and `httpx.AsyncClient` (async) based on a constructor flag, while providing typed dataclass responses with embedded credit metadata, a structured exception hierarchy that distinguishes between rate limits and credit exhaustion (both HTTP 429), and automatic retry with exponential backoff for transient failures.

The KalshiBook API has ~10 data endpoints with consistent patterns: (1) all authenticated endpoints use `Authorization: Bearer kb-...`, (2) all error responses share the same JSON envelope `{"error": {"code": "...", "message": "...", "status": N}, "request_id": "..."}`, (3) credit usage is exposed via response headers `X-Credits-Remaining`, `X-Credits-Used`, `X-Credits-Total`, `X-Credits-Cost`, and (4) both rate limits and credit exhaustion return HTTP 429 but differ in `error.code` (`rate_limit_exceeded` vs `credits_exhausted`). The SDK must parse response bodies to distinguish these cases.

The response model layer uses stdlib `dataclasses` with `slots=True` (available since Python 3.10) and `frozen=True` for immutability. Each response dataclass includes a `@classmethod from_dict(cls, data: dict) -> Self` factory that handles datetime parsing from ISO 8601 strings. Credit metadata is separated into a `ResponseMeta` dataclass attached as `.meta` on every response.

**Primary recommendation:** Use httpx natively in dual mode (not sync-over-async wrapping). Implement `from_dict()` classmethods on all dataclasses for JSON-to-object conversion with datetime parsing. Build retry logic as a custom wrapper around httpx's transport (not tenacity) to keep the dependency tree minimal. Use pytest-httpx for transport-level mocking in tests.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Auth and client construction
- API key as first **positional** arg: `KalshiBook("kb-...")`
- Env var fallback: `KALSHIBOOK_API_KEY` -- `KalshiBook()` reads from env automatically
- `base_url` param with production default -- configurable for local/staging: `KalshiBook("kb-...", base_url="http://localhost:8000")`
- `sync=True` by default (scripts/notebooks are the primary audience). Async users opt in with `sync=False`
- Single `KalshiBook` class (not separate sync/async classes like Tavily)

#### Response model shape
- Stdlib `dataclasses` (no Pydantic) -- already decided
- Field names match API JSON exactly (no renaming)
- Timestamp fields parsed into `datetime` objects (not raw ISO strings) -- consistent with typed philosophy
- Credit/request metadata nested under `.meta` (not top-level)
- `.meta` includes: `credits_used`, `credits_remaining`, `response_time`
- `client.usage()` method for standalone balance check (hits billing API)

#### Exception hierarchy
- All exceptions inherit from `KalshiBookError` base class -- users can `except KalshiBookError` to catch everything
- Specific subclasses: `AuthenticationError`, `RateLimitError`, `CreditsExhaustedError`, `MarketNotFoundError`
- `CreditsExhaustedError` is distinct (not grouped under generic PaymentError) -- users catch it specifically to handle "out of credits" differently
- Every API exception carries: `status_code`, `response_body`, and human-readable `message`
- 429 rate limits: SDK auto-retries with exponential backoff (3 attempts) transparently

#### Credit tracking UX
- Credit metadata always included on every response (not opt-in like Tavily's `include_usage`)
- Accessed via `response.meta.credits_used`, `response.meta.credits_remaining`
- Silent -- no automatic warnings at low balance. User checks `.meta` themselves
- `client.usage()` method available for explicit balance check without a data call

### Claude's Discretion
- Nested vs flat dataclass structure (whether inner objects like orderbook levels get their own dataclass)
- Exact dataclass field ordering
- Whether `.meta` is its own dataclass or a simple NamedTuple

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.27 | HTTP transport (sync `httpx.Client` + async `httpx.AsyncClient`) | Already declared as SDK dependency in Phase 8. Native dual-mode (sync + async) with identical API surface. Connection pooling built in. |
| stdlib dataclasses | (builtin) | Typed response models with `slots=True`, `frozen=True` | Locked decision. Zero dependencies, IDE autocomplete, 3.10+ features (slots, kw_only). |
| stdlib datetime | (builtin) | Timestamp parsing via `datetime.fromisoformat()` | Locked decision to parse timestamps into `datetime` objects. |

### Supporting (dev only, already in sdk/pyproject.toml)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0 | Test runner | All unit tests |
| pytest-asyncio | >=1.0 | Async test support | Testing async client path |
| pytest-httpx | >=0.35 | Mock httpx transport | Mocking API responses without network |
| mypy | >=1.10 | Type checking | Verify dataclass types, `from_dict` signatures |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `from_dict()` | dacite or cattrs library | Adds a dependency for ~50 lines of custom code. SDK has only ~15 model classes -- hand-rolled is simpler and has zero dependency cost. |
| Hand-rolled retry loop | tenacity library | Tenacity is powerful but adds a dependency. The retry logic here is narrow (only 429 rate limits, 3 attempts, exponential backoff). ~20 lines of custom code. |
| Custom transport wrapper | httpx `event_hooks` for retry | Event hooks cannot retry requests -- they only observe. A retry loop wrapping the request call is the correct pattern. |

## Architecture Patterns

### Recommended Project Structure (Phase 9 changes)

```
sdk/src/kalshibook/
├── __init__.py          # Add exception + model re-exports
├── client.py            # KalshiBook class with constructor, usage(), close()
├── models.py            # All response dataclasses + ResponseMeta
├── exceptions.py        # KalshiBookError hierarchy
├── _http.py             # HttpTransport class wrapping httpx Client/AsyncClient
├── _parsing.py          # NEW: from_dict helpers, datetime parsing utility
├── _pagination.py       # (empty stub, filled in Phase 10)
└── py.typed             # (unchanged)
```

### Pattern 1: Dual-Mode HTTP Transport

**What:** A single `HttpTransport` class that creates either `httpx.Client` or `httpx.AsyncClient` based on a `sync` flag. Both httpx clients have identical constructor parameters and method signatures -- the only difference is `await` for async.

**When to use:** Always. This is the core transport abstraction.

**Implementation approach:**

```python
# sdk/src/kalshibook/_http.py
from __future__ import annotations

import time
from typing import Any

import httpx

from kalshibook.exceptions import (
    AuthenticationError,
    CreditsExhaustedError,
    KalshiBookError,
    MarketNotFoundError,
    RateLimitError,
    ValidationError,
)


class HttpTransport:
    """Wraps httpx.Client (sync) or httpx.AsyncClient (async)."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        sync: bool = True,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._sync = sync
        self._max_retries = max_retries
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": f"kalshibook-python/{__version__}",
            "Accept": "application/json",
        }
        client_kwargs = dict(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )
        if sync:
            self._client: httpx.Client | httpx.AsyncClient = httpx.Client(**client_kwargs)
        else:
            self._client = httpx.AsyncClient(**client_kwargs)

    def request_sync(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Sync request with retry on 429 rate limits."""
        # Retry loop with exponential backoff
        ...

    async def request_async(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Async request with retry on 429 rate limits."""
        # Same retry logic but with await and asyncio.sleep
        ...

    def close(self) -> None:
        if self._sync:
            self._client.close()

    async def aclose(self) -> None:
        if not self._sync:
            await self._client.aclose()
```

**Source:** httpx official docs (https://www.python-httpx.org/advanced/clients/, https://www.python-httpx.org/async/)

### Pattern 2: Error Code Mapping (429 Disambiguation)

**What:** The API returns HTTP 429 for both rate limits (`error.code = "rate_limit_exceeded"`) and credit exhaustion (`error.code = "credits_exhausted"`). The SDK must parse the JSON response body to determine which exception to raise.

**When to use:** In the HTTP transport's response handling, after every non-2xx response.

**Implementation approach:**

```python
# Error code to exception class mapping
_ERROR_MAP: dict[str, type[KalshiBookError]] = {
    "invalid_api_key": AuthenticationError,
    "rate_limit_exceeded": RateLimitError,
    "credits_exhausted": CreditsExhaustedError,
    "market_not_found": MarketNotFoundError,
    "event_not_found": MarketNotFoundError,  # or EventNotFoundError if added
    "settlement_not_found": MarketNotFoundError,
    "validation_error": ValidationError,
    "no_data_available": MarketNotFoundError,
}

def _raise_for_status(response: httpx.Response) -> None:
    """Parse error response and raise the appropriate SDK exception."""
    if response.is_success:
        return

    try:
        body = response.json()
        error = body.get("error", {})
        code = error.get("code", "unknown_error")
        message = error.get("message", "An unknown error occurred.")
    except Exception:
        code = "unknown_error"
        message = f"HTTP {response.status_code}"
        body = {}

    exc_class = _ERROR_MAP.get(code, KalshiBookError)
    raise exc_class(
        message=message,
        status_code=response.status_code,
        response_body=body,
    )
```

**Key insight:** The retry loop must check `error.code`, not just HTTP status. A 429 with `credits_exhausted` should NOT be retried (user is out of credits), while a 429 with `rate_limit_exceeded` SHOULD be retried with backoff.

**Source:** KalshiBook API server code at `src/api/errors.py` (direct inspection)

### Pattern 3: Dataclass Response Models with `from_dict()`

**What:** Each API response shape is a `@dataclass(slots=True, frozen=True)` with a `@classmethod from_dict()` factory that parses the JSON dict into a typed instance, converting ISO 8601 strings to `datetime` objects.

**When to use:** For every API response. The `from_dict()` is called in the transport layer after JSON parsing.

**Implementation approach:**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from kalshibook._parsing import parse_datetime


@dataclass(slots=True, frozen=True)
class OrderbookLevel:
    """A single price level in the orderbook."""
    price: int
    quantity: int

    @classmethod
    def from_dict(cls, data: dict) -> OrderbookLevel:
        return cls(price=data["price"], quantity=data["quantity"])


@dataclass(slots=True, frozen=True)
class OrderbookResponse:
    """Reconstructed orderbook state at a specific timestamp."""
    market_ticker: str
    timestamp: datetime
    snapshot_basis: datetime
    deltas_applied: int
    yes: list[OrderbookLevel]
    no: list[OrderbookLevel]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> OrderbookResponse:
        return cls(
            market_ticker=data["market_ticker"],
            timestamp=parse_datetime(data["timestamp"]),
            snapshot_basis=parse_datetime(data["snapshot_basis"]),
            deltas_applied=data["deltas_applied"],
            yes=[OrderbookLevel.from_dict(l) for l in data["yes"]],
            no=[OrderbookLevel.from_dict(l) for l in data["no"]],
            meta=meta,
        )
```

**Source:** Python dataclasses docs (https://docs.python.org/3/library/dataclasses.html)

### Pattern 4: ResponseMeta Dataclass for Credit Tracking

**What:** A small dataclass that wraps credit and request metadata, extracted from response headers. Attached as `.meta` on every response object.

**Implementation approach:**

```python
@dataclass(slots=True, frozen=True)
class ResponseMeta:
    """Credit usage and request metadata from the API response."""
    credits_used: int
    credits_remaining: int
    response_time: float
    request_id: str

    @classmethod
    def from_response(cls, response: httpx.Response) -> ResponseMeta:
        return cls(
            credits_used=int(response.headers.get("X-Credits-Used", 0)),
            credits_remaining=int(response.headers.get("X-Credits-Remaining", 0)),
            response_time=float(response.json().get("response_time", 0.0)),
            request_id=response.headers.get("X-Request-ID", ""),
        )
```

**Recommendation for Claude's Discretion:** Use a `@dataclass(slots=True, frozen=True)` for `ResponseMeta` rather than `NamedTuple`. Reasons: (1) consistent with all other models in the SDK, (2) `slots=True` is equally memory-efficient, (3) dataclasses support `@classmethod` factory methods natively, (4) dataclasses print nicely in notebooks with field names visible.

**Source:** KalshiBook API middleware `inject_credit_headers` in `src/api/main.py` (direct inspection)

### Pattern 5: Client Constructor with Env Var Fallback

**What:** `KalshiBook("kb-...")` with positional API key, env var fallback, format validation, and `sync=True` default.

**Implementation approach:**

```python
class KalshiBook:
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
                message="No API key provided. Pass api_key or set KALSHIBOOK_API_KEY.",
                status_code=0,
                response_body={},
            )
        if not resolved_key.startswith("kb-"):
            raise AuthenticationError(
                message=f"Invalid API key format. Keys must start with 'kb-', got '{resolved_key[:6]}...'",
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
    def from_env(cls, **kwargs) -> KalshiBook:
        """Create client using KALSHIBOOK_API_KEY environment variable."""
        return cls(api_key=None, **kwargs)
```

**Note on `sync` default:** The CONTEXT.md says `sync=True` by default. This differs from the Phase 8 stub docstring which says `Default False (async)`. The CONTEXT.md is the authoritative source -- update the stub to `sync=True`.

### Pattern 6: Exponential Backoff Retry for Rate Limits

**What:** Auto-retry on 429 `rate_limit_exceeded` responses with exponential backoff (base 1s, max ~4s, 3 attempts). Does NOT retry `credits_exhausted`.

**Implementation approach:**

```python
import random
import time

def _retry_delay(attempt: int) -> float:
    """Exponential backoff with jitter: 1s, 2s, 4s base + 0-0.5s jitter."""
    base = min(2 ** attempt, 8)  # 1, 2, 4 for attempts 0, 1, 2
    jitter = random.uniform(0, 0.5)
    return base + jitter

# In the request method:
for attempt in range(max_retries):
    response = client.request(method, path, **kwargs)
    if response.status_code == 429:
        body = response.json()
        error_code = body.get("error", {}).get("code", "")
        if error_code == "credits_exhausted":
            break  # Do NOT retry -- user is out of credits
        # Rate limit -- retry with backoff
        retry_after = response.headers.get("Retry-After")
        delay = float(retry_after) if retry_after else _retry_delay(attempt)
        time.sleep(delay)  # or asyncio.sleep for async
        continue
    break
# After loop: raise if still error
```

### Anti-Patterns to Avoid

- **Wrapping async with `asyncio.run()` for sync mode:** httpx provides a fully native `httpx.Client` for sync. Do NOT create an `AsyncClient` and wrap every call with `asyncio.run()` -- this breaks in Jupyter notebooks (which already have a running event loop) and adds overhead.
- **Using tenacity for retry:** Adds a dependency for 20 lines of custom code. The retry logic is narrow (only 429 rate limits, only 3 attempts).
- **Retrying on `credits_exhausted`:** Both rate limits and credit exhaustion return 429, but they mean different things. Retrying when credits are exhausted wastes time and confuses users.
- **Parsing credit metadata from response body instead of headers:** The API puts credit info in headers (`X-Credits-*`), not in the JSON body. The `response_time` field IS in the body though.
- **Using `NamedTuple` for models with complex nested structures:** NamedTuples cannot have `@classmethod` factory methods and do not support `slots`. Dataclasses are uniformly better for this use case.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP transport (sync + async) | Custom urllib3/aiohttp wrapper | httpx `Client` + `AsyncClient` | httpx provides identical sync/async APIs, connection pooling, timeout config, header injection. Already a dependency. |
| Response mocking in tests | Custom mock classes | pytest-httpx `httpx_mock` fixture | Handles both sync and async mocking, request matching, response assertion. Already in dev dependencies. |
| ISO 8601 datetime parsing | Custom regex parser | `datetime.fromisoformat()` + small `Z` suffix handler | stdlib handles the standard format. Only edge case is `Z` suffix on Python 3.10 (5-line helper). |
| JSON serialization of responses | Custom JSON encoder | `dataclasses.asdict()` for any dict conversion needs | stdlib handles recursive dict conversion of dataclass trees. |

**Key insight:** With httpx + stdlib dataclasses + pytest-httpx, the SDK has zero additional runtime dependencies beyond httpx (which is already declared). All other functionality is stdlib or dev-only.

## Common Pitfalls

### Pitfall 1: 429 Disambiguation -- Rate Limit vs Credits Exhausted

**What goes wrong:** The SDK treats all 429 responses identically, either retrying all of them (wasting time when credits are exhausted) or raising a generic error that users cannot catch specifically.
**Why it happens:** HTTP status codes alone are insufficient. The API uses 429 for two semantically different errors. Developers check `response.status_code` but forget to parse the JSON body.
**How to avoid:** Always parse the response body on 429. Check `error.code` field. Map `rate_limit_exceeded` to `RateLimitError` (retryable) and `credits_exhausted` to `CreditsExhaustedError` (not retryable).
**Warning signs:** Users report "SDK hangs for 10 seconds then fails" when they run out of credits (it was retrying a non-retryable error).

### Pitfall 2: `datetime.fromisoformat()` Rejects `Z` Suffix on Python 3.10

**What goes wrong:** `datetime.fromisoformat("2026-02-17T12:00:00Z")` raises `ValueError` on Python 3.10. Works fine on 3.11+.
**Why it happens:** Python 3.10's `fromisoformat()` only accepts formats produced by `datetime.isoformat()`, which uses `+00:00` not `Z`. Python 3.11 expanded support to accept `Z`.
**How to avoid:** Write a small helper: `def parse_datetime(s: str) -> datetime: return datetime.fromisoformat(s.replace("Z", "+00:00"))`. Use this helper in all `from_dict()` methods instead of calling `fromisoformat` directly.
**Warning signs:** The KalshiBook API server uses `.isoformat()` which produces `+00:00` (safe), but third-party tools or user-provided timestamps might use `Z`.

### Pitfall 3: Forgetting to Close httpx Client

**What goes wrong:** Resource leak warnings in tests and long-running processes. httpx clients hold open TCP connections.
**Why it happens:** Users create `KalshiBook(...)` but never call `.close()` or use a context manager.
**How to avoid:** Implement `__enter__`/`__exit__` (sync) and `__aenter__`/`__aexit__` (async) on `KalshiBook` so users can write `with KalshiBook("kb-...") as client:`. Also implement `__del__` as a safety net (with a warning).
**Warning signs:** "Unclosed client session" warnings in pytest output.

### Pitfall 4: Credit Headers Missing on Error Responses

**What goes wrong:** The SDK tries to read `X-Credits-Remaining` from every response, but error responses (401, 404, 500) do not include credit headers. Parsing fails with `KeyError` or returns `0` incorrectly.
**Why it happens:** The API's `inject_credit_headers` middleware only adds headers when `request.state.credits_remaining` is set, which only happens after the `require_credits` dependency succeeds. Auth failures, 404s, and server errors bypass this path.
**How to avoid:** `ResponseMeta.from_response()` must use `.get()` with defaults for all header values. When credit headers are absent, use sentinel values (e.g., `credits_used=-1` or `credits_remaining=-1`) or make the meta fields `Optional[int]` with `None` default.
**Warning signs:** Users see `credits_remaining: 0` on 401 errors and think they're out of credits.

### Pitfall 5: Sync Client Used in Async Context (or Vice Versa)

**What goes wrong:** User creates `KalshiBook("kb-...", sync=True)` then tries to `await client.get_market(...)`. Or creates with `sync=False` then calls the sync method.
**Why it happens:** Single class serves both modes. The method signatures exist for both but only one mode is active.
**How to avoid:** Each public method should check `self._sync` and raise a clear error if the wrong mode is used: `"Client created with sync=True. Use get_market() instead of await get_market_async()."` Alternatively, provide only one set of methods that automatically dispatch based on the mode.
**Warning signs:** Users get confusing `TypeError: object NoneType can't be used in 'await' expression` or `RuntimeError: cannot be called from a running event loop`.

### Pitfall 6: Retry Loop Swallows the Original Exception

**What goes wrong:** After 3 retry attempts, the SDK raises a generic "max retries exceeded" error, losing the original rate limit error message and response body.
**Why it happens:** The retry loop catches the exception, sleeps, retries, and when max retries are hit, raises a new exception without chaining.
**How to avoid:** Use `raise RateLimitError(...) from last_exception` or simply re-raise the mapped exception from the last response. Always include the original `status_code`, `message`, and `response_body` in the final exception.
**Warning signs:** Users see "max retries exceeded" with no context about what the actual API error was.

## Code Examples

### Complete Exception Hierarchy

```python
# sdk/src/kalshibook/exceptions.py
from __future__ import annotations
from typing import Any


class KalshiBookError(Exception):
    """Base exception for all KalshiBook SDK errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code (0 for client-side errors).
        response_body: Raw API error response dict (empty for client-side errors).
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
        self.response_body = response_body or {}
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
```

### Datetime Parsing Helper (Python 3.10 Safe)

```python
# sdk/src/kalshibook/_parsing.py
from __future__ import annotations

from datetime import datetime, timezone


def parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string to a timezone-aware datetime.

    Handles the 'Z' suffix that datetime.fromisoformat() rejects on Python 3.10.
    Returns None if the input is None.
    """
    if value is None:
        return None
    # Python 3.10 fromisoformat doesn't accept 'Z', 3.11+ does.
    # Normalize to +00:00 for cross-version safety.
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    dt = datetime.fromisoformat(normalized)
    # Ensure timezone-aware (server should always send tz-aware, but be defensive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
```

### Context Manager Support

```python
# In client.py -- KalshiBook class

def __enter__(self) -> KalshiBook:
    return self

def __exit__(self, *args) -> None:
    self.close()

async def __aenter__(self) -> KalshiBook:
    return self

async def __aexit__(self, *args) -> None:
    await self.aclose()

def close(self) -> None:
    """Close the underlying HTTP connection pool (sync)."""
    self._transport.close()

async def aclose(self) -> None:
    """Close the underlying HTTP connection pool (async)."""
    await self._transport.aclose()
```

### Complete Model List (from API source code inspection)

Based on direct inspection of `src/api/models.py` and all route handlers, these are the SDK response dataclasses needed:

| SDK Dataclass | API Response | Endpoint | Notes |
|---------------|-------------|----------|-------|
| `ResponseMeta` | Headers | All endpoints | `credits_used`, `credits_remaining`, `response_time`, `request_id` |
| `OrderbookLevel` | `OrderbookLevel` | POST /orderbook | `price: int`, `quantity: int` |
| `OrderbookResponse` | `OrderbookResponse` | POST /orderbook | Nested `yes`/`no` lists of `OrderbookLevel` |
| `DeltaRecord` | `DeltaRecord` | POST /deltas | Timestamp field parsed to `datetime` |
| `DeltasResponse` | `DeltasResponse` | POST /deltas | Paginated: `data`, `next_cursor`, `has_more` |
| `TradeRecord` | `TradeRecord` | POST /trades | Timestamp field parsed to `datetime` |
| `TradesResponse` | `TradesResponse` | POST /trades | Paginated: `data`, `next_cursor`, `has_more` |
| `MarketSummary` | `MarketSummary` | GET /markets | Optional datetime fields for data coverage |
| `MarketDetail` | `MarketDetail` | GET /markets/{ticker} | Extends MarketSummary with stats |
| `MarketsResponse` | `MarketsResponse` | GET /markets | List of `MarketSummary` |
| `MarketDetailResponse` | `MarketDetailResponse` | GET /markets/{ticker} | Single `MarketDetail` |
| `CandleRecord` | `CandleRecord` | GET /candles/{ticker} | `bucket` as `datetime`, OHLCV ints |
| `CandlesResponse` | `CandlesResponse` | GET /candles/{ticker} | List of `CandleRecord` |
| `SettlementRecord` | `SettlementRecord` | GET /settlements | Optional datetime fields |
| `SettlementResponse` | `SettlementResponse` | GET /settlements/{ticker} | Single `SettlementRecord` |
| `SettlementsResponse` | `SettlementsResponse` | GET /settlements | List of `SettlementRecord` |
| `EventSummary` | `EventSummary` | GET /events | Basic event metadata |
| `EventDetail` | `EventDetail` | GET /events/{event} | Extends EventSummary with nested markets |
| `EventsResponse` | `EventsResponse` | GET /events | List of `EventSummary` |
| `EventDetailResponse` | `EventDetailResponse` | GET /events/{event} | Single `EventDetail` |
| `BillingStatus` | `BillingStatusResponse` | GET /billing/status | For `client.usage()` method |

**Recommendation for Claude's Discretion (nested vs flat):** Use nested dataclasses. Inner objects like `OrderbookLevel`, `DeltaRecord`, `TradeRecord`, `CandleRecord`, `MarketSummary`, `EventSummary`, and `SettlementRecord` each get their own dataclass. This provides maximum type safety and IDE autocomplete. The cost is ~20 small dataclasses, but each is 5-15 lines and trivially simple.

### API Error Response Format

All API errors follow this JSON envelope (verified from `src/api/errors.py`):

```json
{
  "error": {
    "code": "market_not_found",
    "message": "Market 'INVALID' not found.",
    "status": 404
  },
  "request_id": "req_abc123def456"
}
```

Error codes returned by the server (exhaustive list from `src/api/errors.py`):

| Error Code | HTTP Status | SDK Exception | Retryable? |
|-----------|-------------|---------------|------------|
| `invalid_api_key` | 401 | `AuthenticationError` | No |
| `rate_limit_exceeded` | 429 | `RateLimitError` | Yes (backoff) |
| `credits_exhausted` | 429 | `CreditsExhaustedError` | No |
| `market_not_found` | 404 | `MarketNotFoundError` | No |
| `event_not_found` | 404 | `MarketNotFoundError` | No |
| `settlement_not_found` | 404 | `MarketNotFoundError` | No |
| `no_data_available` | 404 | `MarketNotFoundError` | No |
| `validation_error` | 422 | `ValidationError` | No |
| `invalid_timestamp` | 400 | `ValidationError` | No |
| `internal_error` | 500 | `KalshiBookError` | No |

### Credit Response Headers

The API middleware (`inject_credit_headers` in `src/api/main.py`) adds these headers to successful data endpoint responses:

| Header | Type | Description |
|--------|------|-------------|
| `X-Credits-Remaining` | int | Credits left in billing cycle |
| `X-Credits-Used` | int | Total credits consumed in billing cycle |
| `X-Credits-Total` | int | Total credits allocated for billing cycle |
| `X-Credits-Cost` | int | Credits consumed by this specific request |
| `X-Request-ID` | str | Unique request ID for tracing |

**Note:** These headers are ONLY present on successful data endpoint responses (not on auth errors, 404s, or billing endpoints).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests` + `aiohttp` for dual mode | `httpx` for both sync and async | 2023-2024 | Single dependency, identical API, connection pooling in both modes |
| Pydantic models in SDK | Stdlib dataclasses (slots=True) | 2024-2025 | Zero dependency cost, no pydantic-core version conflicts |
| Separate sync/async client classes | Single class with sync flag | Emerging pattern | Simpler API surface, one import, one constructor |
| `datetime.strptime()` for ISO parsing | `datetime.fromisoformat()` | Python 3.7+ | Faster, handles timezone suffixes natively (3.11+ handles Z) |

**Deprecated/outdated:**
- `requests` library for new SDKs: httpx is the modern replacement with async support
- `aiohttp` for SDK clients: httpx replaces the need for a separate async HTTP library
- `dataclasses-json` / `cattrs` for small model sets: hand-rolled `from_dict()` is simpler and dependency-free for ~20 models

## Open Questions

1. **Production base URL**
   - What we know: The constructor needs a default `base_url`. The CONTEXT.md shows `base_url="http://localhost:8000"` as an override example.
   - What's unclear: What is the production URL? Is it `https://api.kalshibook.io`?
   - Recommendation: Use a placeholder like `https://api.kalshibook.io` and document that it can be overridden. The exact URL can be updated before publishing to PyPI.

2. **`from_env()` vs constructor fallback**
   - What we know: Success criteria says both `KalshiBook(api_key="kb-...")` and `KalshiBook.from_env()` must work. The CONTEXT.md says `KalshiBook()` reads from env automatically.
   - What's unclear: Is `from_env()` needed as a separate classmethod if the constructor already falls back to env?
   - Recommendation: Implement both. The constructor with no args reads env. `from_env()` is a convenience alias that makes the intent explicit: `client = KalshiBook.from_env()` is self-documenting. Implement as `return cls(api_key=None, **kwargs)`.

3. **`usage()` method authentication**
   - What we know: `GET /billing/status` requires a Supabase JWT (not an API key). The SDK authenticates with API keys.
   - What's unclear: How does `client.usage()` call the billing endpoint when it only has an API key, not a JWT?
   - Recommendation: The billing status may need a new SDK-facing endpoint that accepts API key auth, OR `usage()` can track credits client-side from response headers (last known `credits_remaining` from the most recent response). Document this as an open question for the planner -- it may require a small server-side change (a `/billing/status` endpoint that accepts API key auth) or a client-side approximation.

4. **`__init__.py` re-exports**
   - What we know: Phase 8 exports only `KalshiBook` and `__version__`.
   - What's unclear: Should Phase 9 re-export all exception classes and model classes from `__init__.py`?
   - Recommendation: Re-export exceptions (`KalshiBookError`, `AuthenticationError`, `RateLimitError`, `CreditsExhaustedError`, `MarketNotFoundError`, `ValidationError`) from `__init__.py`. Users need to catch these. Model classes can also be exported for type annotation convenience. This follows the Stripe SDK pattern.

## Sources

### Primary (HIGH confidence)
- KalshiBook API source code -- `src/api/models.py`, `src/api/errors.py`, `src/api/deps.py`, `src/api/main.py`, and all route handlers (direct inspection, exact JSON shapes and error codes verified)
- httpx official documentation (https://www.python-httpx.org/) -- Client/AsyncClient APIs, transports, timeouts, event hooks
- Python dataclasses documentation (https://docs.python.org/3/library/dataclasses.html) -- `slots=True`, `frozen=True`, `kw_only=True` features for Python 3.10+
- Python datetime documentation (https://docs.python.org/3/library/datetime.html) -- `fromisoformat()` behavior differences between 3.10 and 3.11

### Secondary (MEDIUM confidence)
- pytest-httpx documentation (https://colin-b.github.io/pytest_httpx/) -- mock transport patterns for both sync and async
- Tavily Python SDK source (https://github.com/tavily-ai/tavily-python) -- constructor pattern, env var fallback, error mapping pattern
- Phase 8 research and summary (`.planning/phases/08-sdk-scaffolding/`) -- module structure, pyproject.toml, dependency versions

### Tertiary (LOW confidence)
- None. All findings verified with primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- httpx and stdlib dataclasses are well-documented; API response shapes verified from source code
- Architecture: HIGH -- dual-mode transport pattern verified against httpx docs; error mapping verified against API error codes
- Pitfalls: HIGH -- 429 disambiguation verified from server source; datetime.fromisoformat 3.10/3.11 difference verified from Python docs
- Models: HIGH -- every response dataclass derived from direct inspection of `src/api/models.py` and route handlers

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable libraries, 30-day window appropriate)
