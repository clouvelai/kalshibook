# Orderbook

Reconstruct the full L2 orderbook for any Kalshi market at any point in time.

KalshiBook captures orderbook snapshots and delta streams, then replays them server-side to rebuild the exact orderbook state at your requested timestamp.

## Basic Usage

```python
from datetime import datetime, timezone
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

book = client.get_orderbook(
    "KXBTC-25FEB14-T98250",
    timestamp=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
)

print(f"Market: {book.market_ticker}")
print(f"Timestamp: {book.timestamp}")
print(f"Snapshot basis: {book.snapshot_basis}")
print(f"Deltas applied: {book.deltas_applied}")
```

## Accessing Price Levels

The orderbook has two sides: `yes` and `no`. Each side is a list of `OrderbookLevel` objects with `price` (in cents) and `quantity` fields:

```python
# Print Yes side (bids on the "yes" outcome)
print("YES side:")
for level in book.yes:
    print(f"  {level.price}c  x{level.quantity}")

# Print No side (bids on the "no" outcome)
print("NO side:")
for level in book.no:
    print(f"  {level.price}c  x{level.quantity}")
```

## Limiting Depth

Use the `depth` parameter to limit the number of price levels returned per side:

```python
book = client.get_orderbook(
    "KXBTC-25FEB14-T98250",
    timestamp=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
    depth=5,  # Top 5 levels per side
)

print(f"Yes levels: {len(book.yes)}")  # At most 5
print(f"No levels: {len(book.no)}")    # At most 5
```

## How Reconstruction Works

When you call `get_orderbook()`, the server:

1. Finds the nearest snapshot before your requested timestamp
2. Replays all orderbook deltas between that snapshot and your timestamp
3. Returns the reconstructed L2 state

The `snapshot_basis` field tells you which snapshot was used as the starting point, and `deltas_applied` shows how many delta events were replayed.

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `market_ticker` | `str` | The market ticker |
| `timestamp` | `datetime` | Reconstructed point in time |
| `snapshot_basis` | `datetime` | Snapshot used as reconstruction starting point |
| `deltas_applied` | `int` | Number of deltas replayed from snapshot to timestamp |
| `yes` | `list[OrderbookLevel]` | Yes-side price levels |
| `no` | `list[OrderbookLevel]` | No-side price levels |
| `meta` | `ResponseMeta` | Credit and request metadata |

Each `OrderbookLevel` has:

| Field | Type | Description |
|-------|------|-------------|
| `price` | `int` | Price in cents (1-99) |
| `quantity` | `int` | Number of contracts at this price |

## Credit Tracking

```python
book = client.get_orderbook("KXBTC-25FEB14-T98250", timestamp)

print(f"Credits used: {book.meta.credits_used}")
print(f"Credits remaining: {book.meta.credits_remaining}")
```
