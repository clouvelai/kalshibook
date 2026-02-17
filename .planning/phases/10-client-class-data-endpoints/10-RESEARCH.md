# Phase 10: Client Class and Data Endpoints - Research

**Researched:** 2026-02-17
**Domain:** Python SDK endpoint methods -- wiring typed client methods to KalshiBook API routes via httpx transport, dual sync/async dispatch, ResponseMeta extraction
**Confidence:** HIGH

## Summary

Phase 10 adds the public API methods to the `KalshiBook` client class built in Phase 9. The client already has a working `HttpTransport` with `request_sync()` / `request_async()`, typed response dataclasses with `from_dict()` factories, and a `ResponseMeta.from_headers()` parser. This phase wires endpoint methods onto the client that: (1) accept typed Python arguments (ticker strings, datetime objects, interval strings), (2) dispatch to the correct HTTP method and path via the transport, (3) parse JSON responses into typed dataclass instances with `.meta` credit tracking, and (4) provide both sync and async variants transparently based on the `sync` flag.

The KalshiBook API has 10 data endpoints across 6 route groups. Phase 10 covers the 8 non-paginated endpoints (as specified by requirements DATA-01, DATA-04, DATA-05, DATA-06, DATA-08). The 3 paginated endpoints (deltas, trades, settlements list) are deferred to Phase 11 which adds cursor-based auto-pagination. However, `list_settlements()` (DATA-07) is NOT in Phase 10 requirements, so it belongs to Phase 11.

The central design challenge is the dual-mode dispatch pattern: every public method must work in both sync (`client.get_market("TICKER")`) and async (`await client.get_market("TICKER")`) modes. The recommended pattern is a private `_request()` helper that delegates to `request_sync` or `request_async` based on `self._sync`, returning a parsed `httpx.Response`. Each public method calls `_request()`, then parses the JSON body and headers into the corresponding dataclass using `from_dict()` + `ResponseMeta.from_headers()`.

**Primary recommendation:** Add a private `_request()` method to `KalshiBook` that handles sync/async dispatch and returns an `httpx.Response`. Each endpoint method calls `_request()`, extracts `ResponseMeta` from headers/body, then calls the response model's `from_dict()`. For async mode, each public method returns a coroutine -- the same method name works in both modes by checking `self._sync` and either returning the result directly (sync) or returning an awaitable (async).

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.27 | HTTP transport (already wrapped by `HttpTransport`) | Already a dependency. Transport layer built in Phase 9. |
| stdlib dataclasses | (builtin) | Response models with `from_dict()` factories | All models built in Phase 9. Phase 10 uses them, doesn't create new ones. |
| stdlib datetime | (builtin) | Timestamp parameters (user passes `datetime` to `get_orderbook()`) | ISO format serialization for query params and JSON bodies. |

### Supporting (dev only, already in sdk/pyproject.toml)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0 | Test runner | All endpoint method tests |
| pytest-asyncio | >=1.0 | Async test support | Testing async client method paths |
| pytest-httpx | >=0.35 | Mock httpx transport | Mock all API responses without network |
| mypy | >=1.10 | Type checking | Verify method signatures and return types |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dual-dispatch `_request()` helper | Separate sync/async method names (`get_market()` vs `get_market_async()`) | Explicit naming avoids magic, but doubles the API surface. Single-method-name approach is cleaner for users. |
| `isoformat()` for datetime serialization | strftime custom format | `isoformat()` is the standard, produces what the API expects. No need for custom formatting. |
| Individual query param building | httpx `params=` dict | httpx `params=` handles URL encoding automatically. Use it. |

## Architecture Patterns

### Recommended Project Structure (Phase 10 changes)

```
sdk/src/kalshibook/
+-- __init__.py          # Unchanged (Phase 9)
+-- client.py            # ADD: endpoint methods, _request() helper
+-- models.py            # Unchanged (Phase 9)
+-- exceptions.py        # Unchanged (Phase 9)
+-- _http.py             # Unchanged (Phase 9)
+-- _parsing.py          # Unchanged (Phase 9)
+-- _pagination.py       # Empty stub (filled in Phase 11)
+-- py.typed             # Unchanged
```

Phase 10 modifies only `client.py` -- all infrastructure is already in place.

### Pattern 1: Dual-Mode Request Dispatch

**What:** A private `_request()` method that abstracts sync vs async transport calls. In sync mode, it calls `self._transport.request_sync()` and returns the response directly. In async mode, it calls `self._transport.request_async()` and returns an awaitable.

**When to use:** Every endpoint method delegates through `_request()`.

**Implementation approach:**

```python
# In client.py

def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Dispatch a sync HTTP request through the transport layer."""
    return self._transport.request_sync(method, path, **kwargs)

async def _arequest(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Dispatch an async HTTP request through the transport layer."""
    return self._transport.request_async(method, path, **kwargs)
```

Then each public method has a sync and async form:

```python
def get_market(self, ticker: str) -> MarketDetailResponse:
    """Get full detail for a single market (sync)."""
    resp = self._request("GET", f"/markets/{ticker}")
    body = resp.json()
    meta = ResponseMeta.from_headers(dict(resp.headers), body)
    return MarketDetailResponse.from_dict(body, meta)

async def aget_market(self, ticker: str) -> MarketDetailResponse:
    """Get full detail for a single market (async)."""
    resp = await self._arequest("GET", f"/markets/{ticker}")
    body = resp.json()
    meta = ResponseMeta.from_headers(dict(resp.headers), body)
    return MarketDetailResponse.from_dict(body, meta)
```

**Key design decision:** Use `get_market()` / `aget_market()` naming pattern (prefixed `a` for async). This is the httpx convention (`client.close()` / `client.aclose()`). The alternative (single method name that returns a coroutine in async mode) is fragile -- users must remember to `await` based on a constructor flag, and type checkers cannot narrow the return type.

**Alternative approach -- single method name with branching:**

```python
def get_market(self, ticker: str) -> MarketDetailResponse:
    if self._sync:
        resp = self._transport.request_sync("GET", f"/markets/{ticker}")
    else:
        # Returns a coroutine -- user must await
        return self._aget_market(ticker)  # type: ignore
    body = resp.json()
    meta = ResponseMeta.from_headers(dict(resp.headers), body)
    return MarketDetailResponse.from_dict(body, meta)
```

This is less clean for type checkers (return type is `MarketDetailResponse | Coroutine`) but provides a nicer user API (same method name). The prior art (Phase 9 CONTEXT.md says "Single KalshiBook class with sync=True flag") suggests the user expects a single method name. Recommend the dual-name approach (`get_X` / `aget_X`) for type safety, with the understanding that async users call `await client.aget_market()`.

### Pattern 2: Response Parsing Pipeline

**What:** Every endpoint method follows the same 4-step pipeline: (1) build request params/body, (2) call `_request()` / `_arequest()`, (3) extract `ResponseMeta` from headers+body, (4) call `ResponseModel.from_dict(body, meta)`.

**When to use:** Every endpoint method.

**Implementation approach:**

```python
def _parse_response(self, resp: httpx.Response, model_cls, *, key: str = "") -> Any:
    """Parse an httpx response into a typed model with ResponseMeta.

    If key is provided, extracts body[key] for the model's from_dict.
    If key is empty, passes entire body to from_dict.
    """
    body = resp.json()
    meta = ResponseMeta.from_headers(dict(resp.headers), body)
    return model_cls.from_dict(body, meta)
```

This eliminates duplication across all endpoint methods. Each method becomes:

```python
def list_markets(self) -> MarketsResponse:
    resp = self._request("GET", "/markets")
    return self._parse_response(resp, MarketsResponse)
```

### Pattern 3: POST Body Endpoints (Orderbook)

**What:** The orderbook endpoint uses POST with a JSON body (not GET with query params). The SDK must serialize the `datetime` timestamp to ISO 8601 string.

**When to use:** `get_orderbook()` and any future POST endpoints.

**Implementation approach:**

```python
def get_orderbook(
    self,
    ticker: str,
    timestamp: datetime,
    *,
    depth: int | None = None,
) -> OrderbookResponse:
    """Reconstruct the orderbook at a specific historical timestamp."""
    body: dict[str, Any] = {
        "market_ticker": ticker,
        "timestamp": timestamp.isoformat(),
    }
    if depth is not None:
        body["depth"] = depth
    resp = self._request("POST", "/orderbook", json=body)
    return self._parse_response(resp, OrderbookResponse)
```

**Key detail:** httpx's `json=` parameter automatically serializes the dict and sets `Content-Type: application/json`. Do NOT manually call `json.dumps()`.

### Pattern 4: Query Parameter Endpoints (Candles, Events)

**What:** Candles and events endpoints use GET with query parameters. The SDK converts Python types to query param strings.

**When to use:** `get_candles()`, `list_events()`.

**Implementation approach:**

```python
def get_candles(
    self,
    ticker: str,
    *,
    start_time: datetime,
    end_time: datetime,
    interval: str = "1h",
) -> CandlesResponse:
    """Get OHLCV candlestick data for a market."""
    params: dict[str, Any] = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "interval": interval,
    }
    resp = self._request("GET", f"/candles/{ticker}", params=params)
    return self._parse_response(resp, CandlesResponse)
```

**Key detail:** httpx's `params=` dict automatically URL-encodes values and appends to the URL. Datetime objects should be converted to ISO 8601 strings before passing.

### Pattern 5: Optional Filter Parameters (Events, Settlements)

**What:** Some endpoints accept optional filter query params (category, series_ticker, status). The SDK should only include params that are not None.

**When to use:** `list_events()`, (and `list_settlements()` in Phase 11).

**Implementation approach:**

```python
def list_events(
    self,
    *,
    category: str | None = None,
    series_ticker: str | None = None,
    status: str | None = None,
) -> EventsResponse:
    """List events, optionally filtered by category, series, or status."""
    params: dict[str, str] = {}
    if category is not None:
        params["category"] = category
    if series_ticker is not None:
        params["series_ticker"] = series_ticker
    if status is not None:
        params["status"] = status
    resp = self._request("GET", "/events", params=params)
    return self._parse_response(resp, EventsResponse)
```

### Anti-Patterns to Avoid

- **Manually building URL strings with query params:** Use httpx's `params=` dict. Never concatenate `?key=value` into the path string -- this breaks URL encoding for special characters.
- **Duplicating response parsing logic in every method:** Extract into `_parse_response()` helper. Each endpoint method should be 5-10 lines.
- **Passing raw dict responses to users:** Every endpoint MUST return a typed dataclass. This is Success Criterion 4.
- **Forgetting to handle async variants:** Every public method needs both sync and async forms. Missing async support breaks the `sync=False` contract.
- **Serializing datetime with `str()` instead of `.isoformat()`:** `str(datetime)` adds a space between date and time instead of 'T'. Always use `.isoformat()`.
- **Including `None` values in query params dict:** httpx sends `param=None` as the literal string "None". Filter out None-valued keys before passing to `params=`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL query param encoding | Manual `urllib.parse.urlencode` | httpx `params=` dict | httpx handles encoding, escaping, and appending automatically |
| JSON body serialization | `json.dumps()` + Content-Type header | httpx `json=` kwarg | httpx handles serialization and header injection |
| Response JSON parsing | Custom JSON decoder | `resp.json()` | httpx uses `json.loads()` internally, returns dict |
| ISO 8601 datetime formatting | Custom `strftime` patterns | `datetime.isoformat()` | Standard method, produces the format the API expects |

**Key insight:** httpx's `params=`, `json=`, and `.json()` handle all serialization/deserialization. The SDK methods are thin wrappers: build params -> call transport -> parse response model.

## Common Pitfalls

### Pitfall 1: datetime Serialization Missing Timezone

**What goes wrong:** User passes a naive `datetime` (no timezone) to `get_orderbook(ticker, timestamp)`. The SDK sends `"2026-02-17T12:00:00"` without timezone info. The server may reject it (422 validation_error) or interpret it differently.
**Why it happens:** `datetime.now()` returns a naive datetime by default. Many users forget to use `datetime.now(timezone.utc)`.
**How to avoid:** Document that timestamps must be timezone-aware. Optionally, the SDK can defensively add UTC if `tzinfo is None`: `if timestamp.tzinfo is None: timestamp = timestamp.replace(tzinfo=timezone.utc)`. This matches the defensive pattern already in `_parsing.py`.
**Warning signs:** Users report "invalid_timestamp" ValidationError when passing `datetime.now()`.

### Pitfall 2: Async Method Returns Coroutine, User Forgets await

**What goes wrong:** User creates `KalshiBook("kb-...", sync=False)` then calls `result = client.get_market("TICKER")` without `await`. Gets a coroutine object, not a response.
**Why it happens:** Same method name in both modes, but in async mode the return value is a coroutine.
**How to avoid:** Use separate method names (`get_market` / `aget_market`). Or document clearly that `sync=False` requires `await`. The httpx convention of `a`-prefixed async methods is well-established.
**Warning signs:** Users see `<coroutine object ...>` printed instead of market data.

### Pitfall 3: Passing `params={}` Sends Empty Query String

**What goes wrong:** `GET /events?` with trailing `?` due to empty params dict. Some servers reject this.
**Why it happens:** httpx appends `?` when `params` is a non-None dict, even if empty.
**How to avoid:** Only pass `params=` when the dict has entries. Use `params=params or None` to convert empty dict to None.
**Warning signs:** Unlikely to cause issues with FastAPI, but cleaner to not send empty `?`.

### Pitfall 4: ResponseMeta.from_headers Receives httpx Headers Object, Not dict

**What goes wrong:** `ResponseMeta.from_headers(resp.headers, body)` -- but `resp.headers` is an `httpx.Headers` object (case-insensitive multi-dict), not a plain `dict`. The `.get()` calls work fine on both, but the type annotation says `dict`.
**Why it happens:** The Phase 9 `from_headers` signature accepts `dict` but httpx returns `Headers`.
**How to avoid:** Pass `dict(resp.headers)` to ensure a plain dict, or update the type signature to accept `Mapping[str, str]`. Either works. The code currently uses `.get()` which works on both types, so this is a type annotation issue, not a runtime issue.
**Warning signs:** mypy may flag a type mismatch if strict checking is enabled.

### Pitfall 5: Candle Interval Validation

**What goes wrong:** User passes `interval="5m"` which is not a valid interval. The server returns a 422 ValidationError.
**Why it happens:** The server only supports `1m`, `1h`, `1d` intervals. The SDK doesn't validate before sending.
**How to avoid:** The SDK can optionally validate intervals client-side: `if interval not in ("1m", "1h", "1d"): raise ValueError(...)`. But this couples the SDK to server-side constants. Better to let the server validate and return a typed `ValidationError` -- the SDK already maps this correctly. Document the valid intervals in the method docstring.
**Warning signs:** None -- server validation works fine. Client-side validation is a nice-to-have for faster feedback.

## Code Examples

### Complete Endpoint Method Map

Based on direct inspection of all server-side route handlers and Phase 10 requirements:

| SDK Method | HTTP | Path | Params | Response Model | Requirement |
|------------|------|------|--------|----------------|-------------|
| `get_orderbook(ticker, timestamp, *, depth=None)` | POST | `/orderbook` | JSON body: `{market_ticker, timestamp, depth?}` | `OrderbookResponse` | DATA-01 |
| `list_markets()` | GET | `/markets` | None | `MarketsResponse` | DATA-04 |
| `get_market(ticker)` | GET | `/markets/{ticker}` | Path param | `MarketDetailResponse` | DATA-05 |
| `get_candles(ticker, *, start_time, end_time, interval="1h")` | GET | `/candles/{ticker}` | Query: `start_time, end_time, interval` | `CandlesResponse` | DATA-06 |
| `list_events(*, category=None, series_ticker=None, status=None)` | GET | `/events` | Query: `category?, series_ticker?, status?` | `EventsResponse` | DATA-08 |
| `get_event(event_ticker)` | GET | `/events/{event_ticker}` | Path param | `EventDetailResponse` | DATA-08 |

Endpoints NOT in Phase 10 (deferred to Phase 11 -- paginated):
- `list_deltas(ticker, start_time, end_time)` -- POST `/deltas` (DATA-02)
- `list_trades(ticker, start_time, end_time)` -- POST `/trades` (DATA-03)
- `list_settlements(*, event_ticker=None, result=None)` -- GET `/settlements` (DATA-07)

Billing endpoint (potentially Phase 10):
- `usage()` -- needs a server-side endpoint that accepts API key auth (currently `/billing/status` requires JWT, not API key). See Open Questions.

### Complete Sync Endpoint Example

```python
# get_orderbook -- the most complex endpoint (POST with JSON body)

def get_orderbook(
    self,
    ticker: str,
    timestamp: datetime,
    *,
    depth: int | None = None,
) -> OrderbookResponse:
    """Reconstruct the L2 orderbook state at a specific historical timestamp.

    Parameters
    ----------
    ticker : str
        Kalshi market ticker (e.g., "KXBTC-26FEB17-T50000").
    timestamp : datetime
        Point in time to reconstruct. Must be timezone-aware.
    depth : int, optional
        Limit number of price levels returned. Default: all.

    Returns
    -------
    OrderbookResponse
        Reconstructed orderbook with yes/no levels and credit metadata.

    Raises
    ------
    MarketNotFoundError
        If the market ticker is not found or has no data.
    ValidationError
        If the timestamp is outside the available data range.
    """
    body: dict[str, Any] = {
        "market_ticker": ticker,
        "timestamp": timestamp.isoformat(),
    }
    if depth is not None:
        body["depth"] = depth
    resp = self._request("POST", "/orderbook", json=body)
    return self._parse_response(resp, OrderbookResponse)
```

### Complete Async Endpoint Example

```python
async def aget_orderbook(
    self,
    ticker: str,
    timestamp: datetime,
    *,
    depth: int | None = None,
) -> OrderbookResponse:
    """Reconstruct the L2 orderbook state at a specific timestamp (async)."""
    body: dict[str, Any] = {
        "market_ticker": ticker,
        "timestamp": timestamp.isoformat(),
    }
    if depth is not None:
        body["depth"] = depth
    resp = await self._arequest("POST", "/orderbook", json=body)
    return self._parse_response(resp, OrderbookResponse)
```

### Response Parsing Helper

```python
def _parse_response(self, resp: httpx.Response, model_cls: type) -> Any:
    """Parse httpx response into typed model with ResponseMeta."""
    body = resp.json()
    meta = ResponseMeta.from_headers(dict(resp.headers), body)
    return model_cls.from_dict(body, meta)
```

### Test Pattern with pytest-httpx

```python
import pytest
from datetime import datetime, timezone
from kalshibook import KalshiBook

def test_get_market(httpx_mock):
    """get_market returns typed MarketDetailResponse."""
    httpx_mock.add_response(
        url="https://api.kalshibook.io/markets/KXBTC-TEST",
        json={
            "data": {
                "ticker": "KXBTC-TEST",
                "title": "Test Market",
                "event_ticker": "KXBTC",
                "status": "active",
                "category": "Crypto",
                "first_data_at": "2026-02-01T00:00:00+00:00",
                "last_data_at": "2026-02-17T12:00:00+00:00",
                "rules": None,
                "strike_price": 50000.0,
                "discovered_at": "2026-02-01T00:00:00+00:00",
                "metadata": None,
                "snapshot_count": 100,
                "delta_count": 5000,
            },
            "request_id": "req_test123",
            "response_time": 0.05,
        },
        headers={
            "x-credits-cost": "1",
            "x-credits-remaining": "999",
        },
    )

    client = KalshiBook("kb-test-key")
    result = client.get_market("KXBTC-TEST")

    assert result.data.ticker == "KXBTC-TEST"
    assert result.data.title == "Test Market"
    assert result.meta.credits_remaining == 999
```

### Async Test Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_aget_market(httpx_mock):
    """aget_market returns typed MarketDetailResponse (async)."""
    httpx_mock.add_response(
        url="https://api.kalshibook.io/markets/KXBTC-TEST",
        json={...},  # same as sync test
        headers={...},
    )

    client = KalshiBook("kb-test-key", sync=False)
    result = await client.aget_market("KXBTC-TEST")
    assert result.data.ticker == "KXBTC-TEST"
    await client.aclose()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate sync/async method names everywhere | `a`-prefixed async variants (httpx convention) | 2023+ | Consistent with httpx (`close`/`aclose`), clear which is sync vs async |
| Return raw dicts from SDK methods | Typed dataclass returns with `from_dict()` | Emerging (2024-2025) | IDE autocomplete, type safety, no dict key typos |
| Manual URL building | httpx `params=` and path interpolation | httpx standard | Eliminates URL encoding bugs |
| Separate request building / response parsing | Pipeline pattern (build -> request -> parse) | SDK best practice | Each method is 5-10 lines, consistent structure |

## Open Questions

1. **`usage()` method -- billing endpoint requires JWT, not API key**
   - What we know: Phase 9 CONTEXT.md says `client.usage()` method for standalone balance check. But `GET /billing/status` requires a Supabase JWT (via `get_authenticated_user`), not an API key (via `get_api_key`/`require_credits`).
   - What's unclear: Should the server add a new API-key-authenticated billing endpoint? Or should `usage()` track credits client-side from the last response's `ResponseMeta`?
   - Recommendation: **Defer `usage()` from Phase 10.** The server needs a new endpoint (e.g., `GET /usage` or `GET /billing/usage` accepting API key auth) for this to work. Adding a server endpoint is out of scope for Phase 10 (which is SDK-only). Client-side tracking (storing last `credits_remaining` from response headers) is unreliable (doesn't account for credits used by other API keys). Add a TODO for Phase 11 or a separate server task. Phase 10 success criteria do not include `usage()`.

2. **Async method naming convention: `aget_X` vs same-name dual-dispatch**
   - What we know: Prior decisions say "Single KalshiBook class with sync=True flag." httpx uses `a`-prefixed async variants.
   - What's unclear: Whether the user expects `client.get_market()` to work in both modes (dual-dispatch) or expects separate `get_market()` / `aget_market()` methods.
   - Recommendation: Use the `aget_X` prefix convention. Rationale: (a) matches httpx's own `close()`/`aclose()` convention already used in the KalshiBook client, (b) type checkers can narrow return types, (c) users see a clear error if they call `get_market()` in async mode ("use aget_market instead"), (d) avoids the ugly `Union[T, Coroutine[..., T]]` return type.

3. **`get_settlement(ticker)` -- in Phase 10 or Phase 11?**
   - What we know: Phase 10 requirements are DATA-01, DATA-04, DATA-05, DATA-06, DATA-08. `get_settlement(ticker)` maps to `GET /settlements/{ticker}` which is a non-paginated single-resource endpoint. But DATA-07 is listed under Phase 11.
   - What's unclear: Whether `get_settlement(ticker)` should be added in Phase 10 since it's non-paginated, or kept with Phase 11 since DATA-07 is assigned there.
   - Recommendation: **Keep with Phase 11 as specified.** The roadmap explicitly assigns DATA-07 to Phase 11. Adding it here would be scope creep, even though it's technically non-paginated. Phase 11 can trivially add it alongside `list_settlements()`.

4. **Whether to validate `interval` parameter client-side**
   - What we know: The server only accepts `1m`, `1h`, `1d` intervals. The SDK could validate before sending the request.
   - What's unclear: Whether client-side validation is worth the coupling to server-side constants.
   - Recommendation: **Do not validate client-side.** Let the server return `ValidationError` which the SDK already maps correctly. Document valid intervals in the docstring. This keeps the SDK forward-compatible if the server adds new intervals later.

5. **Whether to defensively make naive datetimes timezone-aware**
   - What we know: The server expects timezone-aware ISO 8601 timestamps. Users may pass naive datetimes.
   - What's unclear: Whether the SDK should auto-add UTC to naive datetimes or raise an error.
   - Recommendation: **Auto-add UTC to naive datetimes with no warning.** This matches the defensive pattern already in `_parsing.py` (parse_datetime assumes UTC for naive values). The server uses FastAPI's datetime parsing which handles ISO 8601 with and without timezone. Adding UTC defensively prevents confusing server-side 422 errors.

## Endpoint-to-Model Mapping (Verified from Source)

Every endpoint, its HTTP method, path, server-side handler, credit cost, and SDK response model:

| Endpoint | HTTP | Path | Handler | Credits | SDK Response Model | SDK Method |
|----------|------|------|---------|---------|--------------------|------------|
| Reconstruct orderbook | POST | `/orderbook` | `routes/orderbook.py:get_orderbook` | 5 | `OrderbookResponse` | `get_orderbook()` |
| List markets | GET | `/markets` | `routes/markets.py:list_markets` | 1 | `MarketsResponse` | `list_markets()` |
| Get market detail | GET | `/markets/{ticker}` | `routes/markets.py:get_market_detail` | 1 | `MarketDetailResponse` | `get_market(ticker)` |
| Get candles | GET | `/candles/{ticker}` | `routes/candles.py:get_candles_endpoint` | 3 | `CandlesResponse` | `get_candles(ticker)` |
| List events | GET | `/events` | `routes/events.py:list_events` | 1 | `EventsResponse` | `list_events()` |
| Get event detail | GET | `/events/{event_ticker}` | `routes/events.py:get_event_detail` | 1 | `EventDetailResponse` | `get_event(event_ticker)` |

Paginated endpoints (Phase 11):
| List deltas | POST | `/deltas` | `routes/deltas.py:get_deltas` | 2 | `DeltasResponse` | `list_deltas()` |
| List trades | POST | `/trades` | `routes/trades.py:get_trades` | 2 | `TradesResponse` | `list_trades()` |
| List settlements | GET | `/settlements` | `routes/settlements.py:list_settlements` | 1 | `SettlementsResponse` | `list_settlements()` |
| Get settlement | GET | `/settlements/{ticker}` | `routes/settlements.py:get_settlement` | 1 | `SettlementResponse` | `get_settlement(ticker)` |

## Server Response Envelope Patterns

Two patterns exist in the API responses -- endpoint methods must handle both:

**Pattern A: Wrapper envelope with `data` key** (Markets, Events, Candles, Settlements)
```json
{
  "data": { ... },
  "request_id": "req_abc",
  "response_time": 0.05
}
```
The SDK models' `from_dict(data, meta)` receive the full body and extract `data["data"]` or `data.get("data", [])` internally.

**Pattern B: Flat response** (Orderbook)
```json
{
  "market_ticker": "TICKER",
  "timestamp": "...",
  "yes": [...],
  "no": [...],
  "request_id": "req_abc",
  "response_time": 0.05
}
```
The `OrderbookResponse.from_dict(data, meta)` receives the full body and extracts top-level fields.

Both patterns include `request_id` and `response_time` at the top level. `ResponseMeta.from_headers()` already extracts `response_time` from the body and `request_id` from the body. Credit info comes from response headers.

## Testing Strategy

### Mock Pattern
Use `pytest-httpx` to mock all HTTP responses. Each test:
1. Register a mock response with expected URL, method, and JSON body
2. Create a `KalshiBook("kb-test-key")` client
3. Call the endpoint method
4. Assert the returned dataclass has correct field values
5. Assert `result.meta.credits_remaining` etc. are parsed correctly

### Test Coverage Matrix
For each of the 6 endpoint methods:
- Sync happy path (correct response, correct model)
- Async happy path (same, but `await` + `sync=False`)
- Error response (404 -> MarketNotFoundError, 422 -> ValidationError)
- ResponseMeta extraction (credit headers parsed correctly)

### Test Structure
```
sdk/tests/
+-- __init__.py              # Existing
+-- test_import.py           # Existing (Phase 8)
+-- test_endpoints.py        # NEW: all endpoint method tests
+-- test_endpoints_async.py  # NEW: async variants (or combined with test_endpoints.py)
```

## Sources

### Primary (HIGH confidence)
- KalshiBook API server source code -- all route handlers in `src/api/routes/` (direct inspection, exact HTTP methods, paths, query params, request bodies, and response JSON shapes verified)
- KalshiBook SDK source code -- `sdk/src/kalshibook/` (direct inspection, all models, exceptions, transport layer verified as built in Phase 9)
- KalshiBook server models -- `src/api/models.py` (direct inspection, Pydantic v2 models show exact field names and types the API returns)
- httpx documentation (https://www.python-httpx.org/) -- `params=`, `json=`, response `.json()`, `Headers` type

### Secondary (MEDIUM confidence)
- Phase 9 Research and Summaries (`.planning/phases/09-*/`) -- architecture decisions, transport patterns, exception mapping
- Phase 9 CONTEXT.md -- locked decisions on auth, response shapes, exception hierarchy, credit tracking

### Tertiary (LOW confidence)
- None. All findings verified from source code and Phase 9 artifacts.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies; everything built on Phase 9 primitives verified from source code
- Architecture: HIGH -- endpoint patterns derived directly from server route handlers; response parsing follows established `from_dict()` + `ResponseMeta.from_headers()` pattern
- Pitfalls: HIGH -- datetime timezone and async naming issues verified against Python docs and httpx conventions
- Testing: HIGH -- pytest-httpx already in dev dependencies; mock patterns verified against pytest-httpx docs

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable SDK patterns, no external dependency changes expected)
