# Phase 11: Pagination and DataFrame Support - Research

**Researched:** 2026-02-17
**Domain:** Cursor-based auto-pagination iterators, optional pandas DataFrame conversion, Python SDK design patterns
**Confidence:** HIGH

## Summary

Phase 11 adds three capabilities to the KalshiBook SDK: (1) auto-paginating iterators for cursor-based endpoints (deltas, trades), (2) non-paginated endpoint methods for settlements, and (3) optional `.to_df()` conversion for any list result. The SDK already has the response models (`DeltasResponse`, `TradesResponse`, `SettlementsResponse`, `SettlementResponse`) with `next_cursor` / `has_more` fields (Phase 9), the HTTP transport with sync/async dispatch (Phase 9), and all non-paginated endpoint methods (Phase 10). The `_pagination.py` module exists as an empty stub waiting to be filled.

The core design challenge is creating a `PageIterator` class that: (a) implements `__iter__`/`__next__` for sync mode and `__aiter__`/`__anext__` for async mode, (b) lazily fetches pages only when the user iterates past the current page, (c) yields individual record dataclasses (e.g., `DeltaRecord`) rather than page objects, and (d) exposes a `.to_df()` method that materializes all remaining items into a pandas DataFrame. The settlements endpoint is NOT paginated server-side (no cursor/has_more), so `list_settlements()` returns a simple response object rather than a `PageIterator` -- but it should still support `.to_df()`.

The pandas optional dependency is already configured in `sdk/pyproject.toml` as `[project.optional-dependencies] pandas = ["pandas>=2.0"]`. The SDK must work without pandas installed (`pip install kalshibook`), with `.to_df()` raising an `ImportError` with a helpful message when pandas is not available. When pandas IS installed (`pip install kalshibook[pandas]`), `.to_df()` converts records to a DataFrame using `dataclasses.asdict()` and the `pd.DataFrame` constructor.

**Primary recommendation:** Implement a generic `PageIterator[T]` class in `_pagination.py` that wraps a "fetch next page" callable and yields `T` items lazily. Each paginated client method (`list_deltas`, `list_trades`) returns a `PageIterator[DeltaRecord]` / `PageIterator[TradeRecord]`. For `.to_df()`, add the method on both `PageIterator` and the non-paginated response classes. Use `dataclasses.asdict()` for conversion, with a lazy `import pandas` inside the method body guarded by try/except `ImportError`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib dataclasses | (builtin) | `asdict()` for DataFrame conversion | Already used for all models. `asdict()` produces dicts that pandas accepts directly. |
| httpx | >=0.27 | HTTP transport (via existing `HttpTransport`) | Already the sole runtime dependency. No new deps needed. |
| pandas | >=2.0 (optional) | DataFrame construction from record dicts | Already declared in `sdk/pyproject.toml` as optional extra. pandas >=2.0 supports dataclass-to-DataFrame since pandas 1.1.0. |

### Supporting (dev only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0 | Test runner | All pagination and DataFrame tests |
| pytest-asyncio | >=1.0 | Async test support | Testing async pagination iterators |
| pytest-httpx | >=0.35 | Mock httpx transport | Multi-page mock response sequences |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `PageIterator` class | Return raw generator from `list_deltas()` | Generator is simpler but cannot attach `.to_df()` method. A class gives us a place to put both iteration and conversion. |
| `dataclasses.asdict()` for DataFrame conversion | `pd.DataFrame([record1, record2, ...])` directly | pandas accepts dataclass lists since 1.1.0, but `asdict()` is more explicit, avoids issues with nested frozen dataclasses, and lets us control which fields appear in the DataFrame. |
| Lazy import of pandas in method body | Top-level `try: import pandas` at module load | Lazy import in method body is the standard pattern (used by pandas itself for optional deps like tabulate). Avoids import-time side effects and keeps the module importable without pandas. |
| Single `PageIterator` for both sync and async | Separate `SyncPageIterator` / `AsyncPageIterator` classes | Single class with both `__iter__`/`__aiter__` is simpler for users (one type to learn). The class can implement both protocols since they don't conflict. |

## Architecture Patterns

### Recommended Project Structure (Phase 11 changes)

```
sdk/src/kalshibook/
+-- __init__.py          # ADD: export PageIterator
+-- client.py            # ADD: list_deltas, list_trades, list_settlements, get_settlement
+-- models.py            # ADD: .to_df() method on list response classes
+-- exceptions.py        # Unchanged
+-- _http.py             # Unchanged
+-- _parsing.py          # Unchanged
+-- _pagination.py       # FILL: PageIterator class
+-- py.typed             # Unchanged
```

### Pattern 1: PageIterator with Lazy Page Fetching

**What:** A generic `PageIterator[T]` class that implements Python's iterator protocol (`__iter__`/`__next__` for sync, `__aiter__`/`__anext__` for async). It holds a reference to a "fetch page" callable, the current page of items, and the cursor for the next page. When the current page is exhausted and `has_more` is True, it calls the fetch function with the cursor to get the next page.

**When to use:** Every cursor-paginated endpoint (`list_deltas`, `list_trades`).

**Implementation approach:**

```python
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Generic, Iterator, TypeVar

T = TypeVar("T")


class PageIterator(Generic[T]):
    """Lazy auto-paginating iterator over cursor-based API results.

    Yields individual records of type T. Fetches subsequent pages
    automatically when the current page is exhausted.

    Supports both sync iteration (for ... in iterator) and async
    iteration (async for ... in iterator).

    Call .to_df() to materialise all remaining records into a
    pandas DataFrame (requires pandas to be installed).
    """

    def __init__(
        self,
        items: list[T],
        has_more: bool,
        next_cursor: str | None,
        fetch_page: Callable[..., tuple[list[T], bool, str | None]],
    ) -> None:
        self._items = items
        self._index = 0
        self._has_more = has_more
        self._next_cursor = next_cursor
        self._fetch_page = fetch_page

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        while self._index >= len(self._items):
            if not self._has_more:
                raise StopIteration
            self._items, self._has_more, self._next_cursor = (
                self._fetch_page(self._next_cursor)
            )
            self._index = 0
        item = self._items[self._index]
        self._index += 1
        return item

    # async variant
    async def __aiter__(self): ...
    async def __anext__(self): ...

    def to_df(self):
        """Materialise all remaining records into a pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for .to_df(). "
                "Install with: pip install kalshibook[pandas]"
            ) from None
        records = list(self)  # consume remaining items
        return pd.DataFrame([asdict(r) for r in records])
```

**Key design decisions:**
- `fetch_page` is a callable that takes a cursor string and returns `(items, has_more, next_cursor)`. This decouples the iterator from the client/transport -- the client methods create a closure that captures the endpoint details.
- The iterator stores the current page items as a list and tracks position with an index. When position reaches the end, it fetches the next page.
- `to_df()` calls `list(self)` to drain remaining items, then converts via `asdict()`. This means items already yielded via `for` loop are NOT included in the DataFrame -- this is documented behaviour.

### Pattern 2: Client Method Returns PageIterator

**What:** Each paginated client method (`list_deltas`, `list_trades`) makes the first API call, parses the response, then wraps the results in a `PageIterator` with a closure for fetching subsequent pages.

**When to use:** `list_deltas()` and `list_trades()`.

**Implementation approach:**

```python
# In client.py

def list_deltas(
    self,
    ticker: str,
    start_time: datetime,
    end_time: datetime,
    *,
    limit: int = 100,
) -> PageIterator[DeltaRecord]:
    """Iterate all orderbook deltas for a market in a time range.

    Auto-paginates: use in a for loop or call .to_df() to
    materialise as a DataFrame.
    """
    def fetch_page(cursor: str | None) -> tuple[list[DeltaRecord], bool, str | None]:
        body: dict[str, Any] = {
            "market_ticker": ticker,
            "start_time": self._ensure_tz(start_time).isoformat(),
            "end_time": self._ensure_tz(end_time).isoformat(),
            "limit": limit,
        }
        if cursor is not None:
            body["cursor"] = cursor
        resp = self._request("POST", "/deltas", json=body)
        parsed = self._parse_response(resp, DeltasResponse)
        return parsed.data, parsed.has_more, parsed.next_cursor

    # Fetch first page eagerly
    first_items, has_more, next_cursor = fetch_page(None)
    return PageIterator(first_items, has_more, next_cursor, fetch_page)
```

**Key design decisions:**
- The first page is fetched eagerly inside `list_deltas()`. This ensures that errors (auth, validation) surface immediately when the method is called, not during the first `next()` call.
- The `fetch_page` closure captures `ticker`, `start_time`, `end_time`, `limit` from the outer scope. Only `cursor` changes per call.
- The method returns `PageIterator[DeltaRecord]`, not `DeltasResponse`. The `PageIterator` yields individual `DeltaRecord` items.

### Pattern 3: Non-Paginated Settlements with .to_df()

**What:** The settlements endpoint is NOT cursor-paginated on the server (no `next_cursor`/`has_more` in the response). `list_settlements()` returns a `SettlementsResponse` directly. The `.to_df()` method is added to `SettlementsResponse` (and potentially all list response classes) so users can still write `client.list_settlements().to_df()`.

**When to use:** `list_settlements()`, and optionally `list_markets()`, `list_events()`, `get_candles()`.

**Implementation approach:**

```python
# Add to_df() to SettlementsResponse in models.py

@dataclass(slots=True, frozen=True)
class SettlementsResponse:
    data: list[SettlementRecord]
    meta: ResponseMeta

    @classmethod
    def from_dict(cls, data: dict, meta: ResponseMeta) -> SettlementsResponse:
        return cls(
            data=[SettlementRecord.from_dict(s) for s in data.get("data", [])],
            meta=meta,
        )

    def to_df(self):
        """Convert settlement records to a pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for .to_df(). "
                "Install with: pip install kalshibook[pandas]"
            ) from None
        from dataclasses import asdict
        return pd.DataFrame([asdict(r) for r in self.data])
```

**Design option -- mixin vs per-class:** A `DataFrameMixin` with a generic `to_df()` could reduce duplication. However, since all response classes are frozen dataclasses with `slots=True`, they cannot use traditional mixin inheritance. Two approaches:

1. **Add `to_df()` directly to each response class** (3-4 classes). Simple, explicit, no inheritance complexity.
2. **Standalone `to_df()` function in a `_dataframe.py` module** that accepts a list of dataclass records. Response classes call this helper.

Recommend option 2: a helper function `records_to_df(records: list[Any]) -> pd.DataFrame` in `_dataframe.py`, called by both `PageIterator.to_df()` and response class `.to_df()` methods. This centralises the pandas import guard and `asdict` logic.

### Pattern 4: Async PageIterator

**What:** The same `PageIterator` class supports async iteration via `__aiter__`/`__anext__`. The `fetch_page` callable must also have an async variant.

**When to use:** `alist_deltas()`, `alist_trades()`.

**Implementation approach:**

```python
# In _pagination.py

class PageIterator(Generic[T]):
    def __init__(
        self,
        items: list[T],
        has_more: bool,
        next_cursor: str | None,
        fetch_page: Callable[..., tuple[list[T], bool, str | None]],
        afetch_page: Callable[..., Any] | None = None,
    ) -> None:
        ...
        self._afetch_page = afetch_page

    def __aiter__(self):
        return self

    async def __anext__(self) -> T:
        while self._index >= len(self._items):
            if not self._has_more:
                raise StopAsyncIteration
            if self._afetch_page is None:
                raise RuntimeError("Async iteration requires sync=False client")
            self._items, self._has_more, self._next_cursor = (
                await self._afetch_page(self._next_cursor)
            )
            self._index = 0
        item = self._items[self._index]
        self._index += 1
        return item
```

The async client methods (`alist_deltas`) pass both `fetch_page` (unused but kept for type consistency) and `afetch_page` to the `PageIterator`.

**Alternative approach -- separate classes:** Use `SyncPageIterator` and `AsyncPageIterator` as separate classes. Cleaner type signatures, but doubles the code. Since the iterator state is identical, recommend a single class with both protocols.

### Pattern 5: Settlements Endpoint Methods

**What:** `list_settlements()` and `get_settlement()` are standard non-paginated endpoint methods following the Phase 10 pattern. `list_settlements()` returns `SettlementsResponse` (with `.to_df()`). `get_settlement()` returns `SettlementResponse`.

**Server endpoint details (from source inspection):**

| Method | HTTP | Path | Query Params | Response |
|--------|------|------|-------------|----------|
| `list_settlements()` | GET | `/settlements` | `event_ticker?`, `result?` | `SettlementsResponse` |
| `get_settlement(ticker)` | GET | `/settlements/{ticker}` | None | `SettlementResponse` |

Neither endpoint uses cursor pagination. The server returns all matching settlements in a single response.

### Anti-Patterns to Avoid

- **Returning a generator from list_deltas():** Generators cannot have `.to_df()` attached. Use a proper class with `__iter__` and `to_df()`.
- **Fetching all pages eagerly in list_deltas():** This defeats the purpose of lazy pagination. The user might only need the first 100 records.
- **Using `pd.DataFrame(records)` directly with dataclass list:** While pandas >=1.1.0 supports this, it doesn't handle nested dataclasses (like `datetime` objects inside `DeltaRecord`) as well as `asdict()` which recursively converts to plain dicts.
- **Top-level `import pandas`:** This would make pandas a hard dependency at import time. The lazy import pattern inside the method body is the standard approach.
- **Mixing sync fetch in async iteration:** If the user creates an async client (`sync=False`), the `__anext__` must use the async fetch function. Using the sync fetch in an async context will block the event loop.
- **Including `meta` (ResponseMeta) in DataFrame output:** The `asdict()` on each record should NOT include the response metadata. Since `meta` is on the parent response class, not on individual records (DeltaRecord, TradeRecord, etc.), this is naturally avoided.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dataclass to dict conversion | Manual field-by-field dict building | `dataclasses.asdict()` | Handles nested dataclasses recursively, handles all field types |
| DataFrame construction | Manual column-by-column building | `pd.DataFrame(list_of_dicts)` | pandas handles type inference, column ordering, index creation |
| Optional dependency guard | Complex importlib tricks | `try: import pandas` in method body | Standard Python pattern, used by pandas itself for its own optional deps |
| Iterator protocol | Manual index tracking with edge cases | `__iter__`/`__next__` with `StopIteration` | Python's iterator protocol is well-defined; follow it exactly |

**Key insight:** The pagination iterator is thin glue -- it connects the existing HTTP transport and response parsing to Python's iterator protocol. The complex parts (HTTP retry, error mapping, response parsing, DataFrame construction) are already solved by existing components.

## Common Pitfalls

### Pitfall 1: PageIterator Reuse After Exhaustion

**What goes wrong:** User iterates through all deltas in a for loop, then calls `.to_df()`. The DataFrame is empty because all items were already consumed.
**Why it happens:** The iterator is single-pass by design (like generators). Once `StopIteration` is raised, subsequent `next()` calls continue to raise `StopIteration`.
**How to avoid:** Document that `.to_df()` materialises REMAINING items. If the user wants all items in a DataFrame, they should call `.to_df()` immediately without iterating first. Alternatively, consider collecting already-yielded items internally so `.to_df()` can return ALL items.
**Recommendation:** Collect ALL yielded items in an internal list (`_consumed`). `.to_df()` then materialises remaining items AND prepends `_consumed`. This is the most user-friendly behaviour -- `.to_df()` always returns ALL data, regardless of how much was iterated.
**Warning signs:** Users complaining about empty DataFrames.

### Pitfall 2: datetime Objects in DataFrame Columns

**What goes wrong:** `dataclasses.asdict()` converts `datetime` objects to `datetime` objects in dicts. pandas keeps them as `datetime` objects in the resulting DataFrame. This is actually correct -- but users might expect timezone-naive timestamps or string timestamps.
**Why it happens:** Our `parse_datetime()` always returns timezone-aware datetimes. `asdict()` preserves them.
**How to avoid:** This is actually the correct behaviour. pandas handles timezone-aware datetimes well. Document that timestamp columns are timezone-aware `datetime64[ns, UTC]` in the DataFrame.
**Warning signs:** None -- this works correctly.

### Pitfall 3: Memory Accumulation with Large Paginated Results

**What goes wrong:** User calls `.to_df()` on a paginated result with millions of deltas. All records must be loaded into memory before DataFrame construction.
**Why it happens:** `.to_df()` calls `list(self)` to drain the iterator, then builds a list of dicts, then builds the DataFrame. Peak memory is ~3x the final DataFrame size.
**How to avoid:** Document memory implications. For truly massive datasets, users should iterate and process in batches rather than calling `.to_df()`. Consider adding a `limit` parameter to `.to_df(max_records=10000)` to prevent accidental OOM.
**Warning signs:** Users experiencing memory pressure on large time ranges.

### Pitfall 4: Server Rate Limiting During Rapid Pagination

**What goes wrong:** Auto-pagination fires requests as fast as the user iterates. If the user does `df = client.list_deltas(...).to_df()`, this sends N sequential requests as fast as possible. If N is large, rate limiting kicks in.
**Why it happens:** The HttpTransport already handles rate limit retries with exponential backoff (Phase 9). But the user may not expect pagination to trigger rate limits.
**How to avoid:** The existing retry logic in `HttpTransport.request_sync()` handles this transparently. The user might see slightly slower iteration as backoff kicks in, but it will work. No additional handling needed in the PageIterator.
**Warning signs:** Iteration becoming progressively slower (normal behaviour as retry kicks in).

### Pitfall 5: Empty First Page

**What goes wrong:** User calls `list_deltas(ticker, start, end)` for a time range with no data. The first page returns `data=[], has_more=False`. The `PageIterator` is created with an empty items list.
**Why it happens:** Normal behaviour for empty result sets.
**How to avoid:** `PageIterator` handles this correctly -- `__next__` immediately raises `StopIteration` when items is empty and `has_more` is False. `.to_df()` returns an empty DataFrame with correct column names. Ensure the empty DataFrame has the right columns by passing `columns=[...]` to the constructor.
**Warning signs:** None if handled correctly. Bug if the DataFrame has no columns on empty results.

### Pitfall 6: Frozen Dataclass Prevents Adding to_df() Method

**What goes wrong:** All SDK response dataclasses use `@dataclass(slots=True, frozen=True)`. You cannot add methods to frozen dataclasses after class definition.
**Why it happens:** `frozen=True` prevents attribute mutation, not method addition. Methods CAN be defined in the class body of a frozen dataclass. `slots=True` restricts instance attribute creation, not class methods.
**How to avoid:** Simply add `to_df()` as a method in the class body. `frozen=True` and `slots=True` do not prevent method definitions -- they only restrict instance attribute assignment.
**Warning signs:** None -- this is a non-issue that might cause confusion during planning.

## Code Examples

### Complete PageIterator Implementation

```python
# sdk/src/kalshibook/_pagination.py

from __future__ import annotations

from dataclasses import asdict
from typing import Any, AsyncIterator, Callable, Coroutine, Generic, Iterator, TypeVar

T = TypeVar("T")

# Type aliases for the fetch-page callables
SyncFetcher = Callable[[str | None], tuple[list[T], bool, str | None]]
AsyncFetcher = Callable[[str | None], Coroutine[Any, Any, tuple[list[T], bool, str | None]]]


class PageIterator(Generic[T]):
    """Lazy auto-paginating iterator over cursor-based API results.

    Yields individual records of type T. Fetches subsequent pages
    automatically when the current page is exhausted.

    Supports sync iteration::

        for delta in client.list_deltas("TICKER", start, end):
            print(delta.price_cents)

    Supports async iteration::

        async for delta in client.alist_deltas("TICKER", start, end):
            print(delta.price_cents)

    Convert to DataFrame::

        df = client.list_deltas("TICKER", start, end).to_df()
    """

    def __init__(
        self,
        items: list[T],
        has_more: bool,
        next_cursor: str | None,
        fetch_page: SyncFetcher | None = None,
        afetch_page: AsyncFetcher | None = None,
    ) -> None:
        self._items = items
        self._index = 0
        self._has_more = has_more
        self._next_cursor = next_cursor
        self._fetch_page = fetch_page
        self._afetch_page = afetch_page
        self._consumed: list[T] = []

    # -- Sync iteration --

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        while self._index >= len(self._items):
            if not self._has_more:
                raise StopIteration
            if self._fetch_page is None:
                raise RuntimeError(
                    "Synchronous iteration requires a sync client (sync=True)"
                )
            self._items, self._has_more, self._next_cursor = self._fetch_page(
                self._next_cursor
            )
            self._index = 0
        item = self._items[self._index]
        self._index += 1
        self._consumed.append(item)
        return item

    # -- Async iteration --

    def __aiter__(self) -> AsyncIterator[T]:
        return self  # type: ignore[return-value]

    async def __anext__(self) -> T:
        while self._index >= len(self._items):
            if not self._has_more:
                raise StopAsyncIteration
            if self._afetch_page is None:
                raise RuntimeError(
                    "Async iteration requires an async client (sync=False)"
                )
            self._items, self._has_more, self._next_cursor = await self._afetch_page(
                self._next_cursor
            )
            self._index = 0
        item = self._items[self._index]
        self._index += 1
        self._consumed.append(item)
        return item

    # -- DataFrame conversion --

    def to_df(self) -> Any:
        """Materialise all records into a pandas DataFrame.

        Drains remaining pages and combines with already-iterated records.
        Requires pandas: pip install kalshibook[pandas]
        """
        remaining = list(self)  # drain remaining via __next__
        all_records = self._consumed  # _consumed already includes remaining
        return _records_to_df(all_records)


def _records_to_df(records: list) -> Any:
    """Convert a list of dataclass records to a pandas DataFrame.

    Raises ImportError with install instructions if pandas is not available.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required for .to_df(). "
            "Install with: pip install kalshibook[pandas]"
        ) from None
    if not records:
        return pd.DataFrame()
    return pd.DataFrame([asdict(r) for r in records])
```

### Client Method for list_deltas (sync)

```python
def list_deltas(
    self,
    ticker: str,
    start_time: datetime,
    end_time: datetime,
    *,
    limit: int = 100,
) -> PageIterator[DeltaRecord]:
    """Iterate all orderbook deltas for *ticker* in [start_time, end_time].

    Auto-paginates across all pages.  Use in a for loop::

        for delta in client.list_deltas("TICKER", start, end):
            print(delta.price_cents, delta.delta_amount)

    Or materialise as a DataFrame::

        df = client.list_deltas("TICKER", start, end).to_df()
    """
    st = self._ensure_tz(start_time).isoformat()
    et = self._ensure_tz(end_time).isoformat()

    def fetch_page(cursor: str | None) -> tuple[list[DeltaRecord], bool, str | None]:
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
        return parsed.data, parsed.has_more, parsed.next_cursor

    items, has_more, next_cursor = fetch_page(None)
    return PageIterator(items, has_more, next_cursor, fetch_page=fetch_page)
```

### Client Method for alist_deltas (async)

```python
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

    async def afetch_page(cursor: str | None) -> tuple[list[DeltaRecord], bool, str | None]:
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
        return parsed.data, parsed.has_more, parsed.next_cursor

    items, has_more, next_cursor = await afetch_page(None)
    return PageIterator(items, has_more, next_cursor, afetch_page=afetch_page)
```

### .to_df() on Non-Paginated Response

```python
# Add to SettlementsResponse, MarketsResponse, EventsResponse, CandlesResponse

def to_df(self) -> Any:
    """Convert records to a pandas DataFrame.

    Requires pandas: pip install kalshibook[pandas]
    """
    from kalshibook._pagination import _records_to_df
    return _records_to_df(self.data)
```

### Test Pattern: Multi-Page Pagination

```python
def test_list_deltas_multi_page(httpx_mock):
    """list_deltas auto-paginates across multiple pages."""
    # Page 1: has_more=True, cursor provided
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json={
            "data": [
                {"market_ticker": "T", "ts": TS, "seq": 1, "price_cents": 50,
                 "delta_amount": 10, "side": "yes"},
            ],
            "next_cursor": "cursor_abc",
            "has_more": True,
            "request_id": "req1",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )
    # Page 2: has_more=False, no cursor
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json={
            "data": [
                {"market_ticker": "T", "ts": TS, "seq": 2, "price_cents": 51,
                 "delta_amount": -5, "side": "no"},
            ],
            "next_cursor": None,
            "has_more": False,
            "request_id": "req2",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    deltas = list(client.list_deltas("T", START, END, limit=1))

    assert len(deltas) == 2
    assert deltas[0].seq == 1
    assert deltas[1].seq == 2
    client.close()
```

### Test Pattern: .to_df() Conversion

```python
def test_to_df_creates_dataframe(httpx_mock):
    """PageIterator.to_df() returns a pandas DataFrame with correct columns."""
    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json={
            "data": [
                {"market_ticker": "T", "ts": TS, "seq": 1, "price_cents": 50,
                 "delta_amount": 10, "side": "yes"},
                {"market_ticker": "T", "ts": TS, "seq": 2, "price_cents": 55,
                 "delta_amount": -3, "side": "no"},
            ],
            "next_cursor": None,
            "has_more": False,
            "request_id": "req1",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    df = client.list_deltas("T", START, END).to_df()

    assert len(df) == 2
    assert list(df.columns) == ["market_ticker", "ts", "seq", "price_cents",
                                  "delta_amount", "side"]
    assert df.iloc[0]["price_cents"] == 50
    client.close()
```

### Test Pattern: pandas Not Installed

```python
def test_to_df_raises_without_pandas(httpx_mock, monkeypatch):
    """to_df() raises ImportError with helpful message when pandas missing."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("No module named 'pandas'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    httpx_mock.add_response(
        url=f"{BASE_URL}/deltas",
        method="POST",
        json={
            "data": [],
            "next_cursor": None,
            "has_more": False,
            "request_id": "req1",
            "response_time": 0.01,
        },
        headers=CREDIT_HEADERS,
    )

    client = KalshiBook("kb-test-key")
    iterator = client.list_deltas("T", START, END)

    with pytest.raises(ImportError, match="kalshibook\\[pandas\\]"):
        iterator.to_df()
    client.close()
```

## Endpoint-to-Method Mapping for Phase 11

| SDK Method | HTTP | Path | Params | Response / Return | Requirement |
|------------|------|------|--------|-------------------|-------------|
| `list_deltas(ticker, start_time, end_time, *, limit=100)` | POST | `/deltas` | JSON body: `{market_ticker, start_time, end_time, cursor?, limit}` | `PageIterator[DeltaRecord]` | DATA-02 |
| `alist_deltas(...)` | POST | `/deltas` | (same, async) | `PageIterator[DeltaRecord]` | DATA-02 |
| `list_trades(ticker, start_time, end_time, *, limit=100)` | POST | `/trades` | JSON body: `{market_ticker, start_time, end_time, cursor?, limit}` | `PageIterator[TradeRecord]` | DATA-03 |
| `alist_trades(...)` | POST | `/trades` | (same, async) | `PageIterator[TradeRecord]` | DATA-03 |
| `list_settlements(*, event_ticker=None, result=None)` | GET | `/settlements` | Query: `event_ticker?`, `result?` | `SettlementsResponse` | DATA-07 |
| `alist_settlements(...)` | GET | `/settlements` | (same, async) | `SettlementsResponse` | DATA-07 |
| `get_settlement(ticker)` | GET | `/settlements/{ticker}` | Path param | `SettlementResponse` | DATA-07 |
| `aget_settlement(ticker)` | GET | `/settlements/{ticker}` | (same, async) | `SettlementResponse` | DATA-07 |

## Server Response Shapes (Verified from Source)

### Deltas Response (Paginated)

```json
{
    "data": [
        {
            "market_ticker": "KXBTC-TEST",
            "ts": "2026-01-15T12:00:00+00:00",
            "seq": 1,
            "price_cents": 55,
            "delta_amount": 10,
            "side": "yes"
        }
    ],
    "next_cursor": "eyJ0cyI6ICIyMDI2LTAxLTE1VDEyOjAwOjAwKzAwOjAwIiwgImlkIjogMX0=",
    "has_more": true,
    "request_id": "req_abc",
    "response_time": 0.05
}
```

Cursor is base64-encoded `{"ts": "...", "id": N}` (opaque to SDK).

### Trades Response (Paginated)

```json
{
    "data": [
        {
            "trade_id": "trade_123",
            "market_ticker": "KXBTC-TEST",
            "yes_price": 55,
            "no_price": 45,
            "count": 10,
            "taker_side": "yes",
            "ts": "2026-01-15T12:00:00+00:00"
        }
    ],
    "next_cursor": "...",
    "has_more": true,
    "request_id": "req_abc",
    "response_time": 0.03
}
```

### Settlements Response (NOT Paginated)

```json
{
    "data": [
        {
            "market_ticker": "KXBTC-TEST",
            "event_ticker": "KXBTC",
            "result": "yes",
            "settlement_value": 100,
            "determined_at": "2026-01-15T12:00:00+00:00",
            "settled_at": "2026-01-15T12:05:00+00:00"
        }
    ],
    "request_id": "req_abc",
    "response_time": 0.02
}
```

No `next_cursor` or `has_more` -- all results returned in one response.

### Settlement (Single) Response

```json
{
    "data": {
        "market_ticker": "KXBTC-TEST",
        "event_ticker": "KXBTC",
        "result": "yes",
        "settlement_value": 100,
        "determined_at": "2026-01-15T12:00:00+00:00",
        "settled_at": "2026-01-15T12:05:00+00:00"
    },
    "request_id": "req_abc",
    "response_time": 0.01
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Return page objects, user manages cursors | Auto-paginating iterators yielding items | 2022+ (Stripe, OpenAI, Databricks SDKs) | Users write `for item in client.list_X()` -- no cursor management |
| pandas as required dependency in SDKs | pandas as optional extra with lazy import | 2023+ (standard practice) | `pip install sdk` stays lightweight; `pip install sdk[pandas]` adds DataFrame support |
| Separate sync/async iterator classes | Single class implementing both `__iter__` and `__aiter__` | Emerging pattern | Fewer classes, same object can be used in both contexts |
| `asdict()` conversion for DataFrames | Direct pandas dataclass support (since pandas 1.1.0) | 2020 (pandas 1.1.0) | Both approaches work; `asdict()` is more explicit and handles edge cases better |

## Open Questions

1. **Should `.to_df()` include already-iterated items or only remaining items?**
   - What we know: If a user does `for x in iterator: ... ; df = iterator.to_df()`, should `df` contain all items or only un-iterated items?
   - Recommendation: **Include ALL items.** Track consumed items in `_consumed` list. `.to_df()` drains remaining and returns all. This is the least surprising behaviour. The Stripe SDK's `auto_paging_iter()` drains all items when materialised.

2. **Should non-paginated list responses (MarketsResponse, EventsResponse, CandlesResponse) also get `.to_df()`?**
   - What we know: DFRA-01 says "All list/paginated responses support .to_df()". This implies yes.
   - Recommendation: **Yes, add `.to_df()` to all list response classes** (MarketsResponse, EventsResponse, CandlesResponse, SettlementsResponse). Use the shared `_records_to_df()` helper. This is 4 one-line method additions.

3. **Should `PageIterator` support `len()`?**
   - What we know: The total count is not known upfront (cursor pagination doesn't provide total count).
   - Recommendation: **Do not implement `__len__`.** This would require fetching all pages to determine length, defeating lazy evaluation. Users who need the count can `len(list(iterator))` or `len(df)` after `.to_df()`.

4. **Should `list_settlements()` return a `PageIterator` for API consistency, even though it's not paginated?**
   - What we know: The server does NOT paginate settlements. Wrapping in `PageIterator` with `has_more=False` would work but adds unnecessary overhead.
   - Recommendation: **Return `SettlementsResponse` directly.** It already has a `.data` list and will get `.to_df()`. Wrapping in `PageIterator` for a non-paginated endpoint is misleading. The success criteria says "auto-pagination" for settlements, but the server already returns all results. The user gets `client.list_settlements().to_df()` which satisfies the criteria.

5. **How to handle `.to_df()` on empty results?**
   - What we know: `pd.DataFrame()` returns an empty DataFrame with no columns. Users may expect column names even on empty results.
   - Recommendation: **Return `pd.DataFrame()` for empty results.** The columns will be inferred when there are records. For empty results, an empty DataFrame (no columns) is acceptable and consistent with pandas behaviour. If column names are desired for empty results, pass `columns=[field.name for field in dataclasses.fields(record_cls)]` -- but this requires knowing the record class at construction time.

## Sources

### Primary (HIGH confidence)
- KalshiBook server source code: `src/api/routes/deltas.py`, `src/api/routes/trades.py`, `src/api/routes/settlements.py` -- exact HTTP methods, pagination patterns, cursor encoding, response shapes verified by direct inspection
- KalshiBook SDK source code: `sdk/src/kalshibook/` -- all existing models, client methods, transport layer, pagination stub verified by direct inspection
- KalshiBook server models: `src/api/models.py` -- `DeltasRequest`, `TradesRequest`, `DeltasResponse`, `TradesResponse`, `SettlementsResponse` Pydantic models verified
- Python stdlib documentation: `dataclasses.asdict()` behaviour, iterator protocol (`__iter__`/`__next__`, `__aiter__`/`__anext__`)
- pandas documentation (https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) -- DataFrame constructor accepts dataclass lists since pandas 1.1.0

### Secondary (MEDIUM confidence)
- Stripe Python SDK auto-pagination pattern (https://docs.stripe.com/api/pagination/auto?lang=python) -- `auto_paging_iter()` pattern verified via official docs
- OpenAI Python SDK pagination (https://github.com/openai/openai-python/blob/main/src/openai/pagination.py) -- `SyncCursorPage`/`AsyncCursorPage` pattern verified via source
- Databricks SDK pagination (https://databricks-sdk-py.readthedocs.io/en/latest/pagination.html) -- `Iterator[T]` abstraction verified via official docs
- Google API Core page iterator (https://googleapis.dev/python/google-api-core/latest/page_iterator.html) -- `HTTPIterator` pattern verified via official docs
- pandas GitHub PR #27999 -- dataclass support added in pandas 1.1.0 (https://github.com/pandas-dev/pandas/pull/27999)

### Tertiary (LOW confidence)
- None. All findings verified from source code or official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies; pandas already declared as optional extra; all patterns use existing SDK primitives
- Architecture: HIGH -- `PageIterator` pattern directly derived from Stripe/OpenAI/Databricks SDK precedents; server pagination shapes verified from source code
- Pitfalls: HIGH -- iterator exhaustion, memory accumulation, and optional dependency patterns are well-documented concerns with known solutions
- Testing: HIGH -- pytest-httpx sequential mock responses handle multi-page scenarios; monkeypatch handles pandas-not-installed tests

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable patterns, no external dependency changes expected)
