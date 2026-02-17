# Deltas

Retrieve raw orderbook delta events -- the individual order additions, removals, and modifications that change the orderbook over time.

## Basic Usage

`list_deltas()` returns a `PageIterator` that automatically fetches subsequent pages:

```python
from datetime import datetime, timezone
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

start = datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc)
end = datetime(2025, 2, 14, 13, 0, tzinfo=timezone.utc)

for delta in client.list_deltas("KXBTC-25FEB14-T98250", start, end):
    print(
        f"[{delta.ts}] seq={delta.seq} "
        f"{delta.side} {delta.price_cents}c "
        f"delta={delta.delta_amount:+d}"
    )
```

## Auto-Pagination

Delta queries can return thousands of records. The `PageIterator` handles pagination transparently -- just iterate normally and pages are fetched on demand:

```python
deltas = client.list_deltas("KXBTC-25FEB14-T98250", start, end)

count = 0
for delta in deltas:
    count += 1

print(f"Total deltas: {count}")
```

You can control the page size with the `limit` parameter:

```python
# Fetch 500 records per page instead of the default 100
deltas = client.list_deltas(
    "KXBTC-25FEB14-T98250", start, end,
    limit=500,
)
```

## Convert to DataFrame

Call `.to_df()` on the `PageIterator` to drain all pages and return a DataFrame:

```python
df = client.list_deltas("KXBTC-25FEB14-T98250", start, end).to_df()

print(df.head())
print(f"Total records: {len(df)}")
```

!!! note
    `.to_df()` drains all remaining pages before converting. If you have already partially iterated, the DataFrame will still include all records (both previously yielded and remaining).

!!! tip
    DataFrame conversion requires `pip install kalshibook[pandas]`.

## Understanding Delta Records

Each `DeltaRecord` represents a change to the orderbook at a specific price level:

- A **positive** `delta_amount` means contracts were added at that price
- A **negative** `delta_amount` means contracts were removed
- `side` indicates whether the change is on the `"yes"` or `"no"` side

Replaying deltas in sequence from a known snapshot reconstructs the orderbook at any point in time. This is exactly what `get_orderbook()` does server-side.

## DeltaRecord Fields

| Field | Type | Description |
|-------|------|-------------|
| `market_ticker` | `str` | Market ticker |
| `ts` | `datetime` | Timestamp of the delta event |
| `seq` | `int` | Sequence number for ordering |
| `price_cents` | `int` | Price level in cents (1-99) |
| `delta_amount` | `int` | Change in quantity (positive = added, negative = removed) |
| `side` | `str` | Orderbook side (`"yes"` or `"no"`) |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ticker` | `str` | required | Market ticker |
| `start_time` | `datetime` | required | Start of range (inclusive). Naive datetimes assumed UTC. |
| `end_time` | `datetime` | required | End of range (exclusive). Naive datetimes assumed UTC. |
| `limit` | `int` | `100` | Page size |
