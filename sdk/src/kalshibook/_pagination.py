"""Cursor-based pagination helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Generic,
    Iterator,
    TypeVar,
)

T = TypeVar("T")

SyncFetcher = Callable[[str | None], tuple[list[Any], bool, str | None]]
"""Callable that fetches the next page given a cursor.

Returns ``(items, has_more, next_cursor)``.
"""

AsyncFetcher = Callable[
    [str | None], Coroutine[Any, Any, tuple[list[Any], bool, str | None]]
]
"""Async callable that fetches the next page given a cursor.

Returns ``(items, has_more, next_cursor)``.
"""


def _records_to_df(records: list[Any]) -> Any:
    """Convert a list of dataclass records to a pandas DataFrame.

    Raises :class:`ImportError` with install instructions when pandas is not
    available.
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


class PageIterator(Generic[T]):
    """Auto-paginating iterator over cursor-based API results.

    Supports both synchronous (``for item in iterator``) and asynchronous
    (``async for item in iterator``) iteration.  Tracks every yielded item
    internally so that :meth:`to_df` always returns the complete result set.

    Parameters
    ----------
    items:
        Records from the first page (already fetched).
    has_more:
        Whether additional pages exist after the first page.
    next_cursor:
        Cursor for the next page, or ``None`` if no more pages.
    fetch_page:
        Synchronous page-fetcher used by ``__next__``.
    afetch_page:
        Asynchronous page-fetcher used by ``__anext__``.
    """

    def __init__(
        self,
        items: list[T],
        has_more: bool,
        next_cursor: str | None,
        fetch_page: SyncFetcher | None = None,
        afetch_page: AsyncFetcher | None = None,
    ) -> None:
        self._items: list[T] = items
        self._index: int = 0
        self._has_more: bool = has_more
        self._next_cursor: str | None = next_cursor
        self._fetch_page = fetch_page
        self._afetch_page = afetch_page
        self._consumed: list[T] = []

    # ------------------------------------------------------------------
    # Sync iteration
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        if self._index >= len(self._items):
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
            if not self._items:
                raise StopIteration

        item = self._items[self._index]
        self._index += 1
        self._consumed.append(item)
        return item

    # ------------------------------------------------------------------
    # Async iteration
    # ------------------------------------------------------------------

    def __aiter__(self) -> AsyncIterator[T]:
        return self  # type: ignore[return-value]

    async def __anext__(self) -> T:
        if self._index >= len(self._items):
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
            if not self._items:
                raise StopAsyncIteration

        item = self._items[self._index]
        self._index += 1
        self._consumed.append(item)
        return item

    # ------------------------------------------------------------------
    # DataFrame conversion
    # ------------------------------------------------------------------

    def to_df(self) -> Any:
        """Materialise all records into a pandas DataFrame.

        Drains any remaining pages first, then returns a DataFrame containing
        **every** record (including those already yielded by iteration).

        Requires pandas: ``pip install kalshibook[pandas]``
        """
        # Drain remaining items via sync iteration
        list(self)
        return _records_to_df(self._consumed)
