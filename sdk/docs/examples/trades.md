# Trades

Retrieve individual trade records for any market over a time range.

## Basic Usage

`list_trades()` returns a `PageIterator` that automatically fetches subsequent pages:

```python
from datetime import datetime, timezone
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

start = datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc)
end = datetime(2025, 2, 14, 13, 0, tzinfo=timezone.utc)

for trade in client.list_trades("KXBTC-25FEB14-T98250", start, end):
    print(
        f"[{trade.ts}] {trade.trade_id} "
        f"yes={trade.yes_price}c no={trade.no_price}c "
        f"x{trade.count} taker={trade.taker_side}"
    )
```

## Auto-Pagination

Trade queries can return large result sets. The `PageIterator` handles pagination transparently:

```python
trades = client.list_trades("KXBTC-25FEB14-T98250", start, end)

total_volume = 0
for trade in trades:
    total_volume += trade.count

print(f"Total volume: {total_volume} contracts")
```

Control the page size with `limit`:

```python
trades = client.list_trades(
    "KXBTC-25FEB14-T98250", start, end,
    limit=500,
)
```

## Convert to DataFrame

```python
df = client.list_trades("KXBTC-25FEB14-T98250", start, end).to_df()

print(df.head())
print(f"Total trades: {len(df)}")

# Analyze by taker side
print(df.groupby("taker_side")["count"].sum())
```

!!! note
    `.to_df()` drains all remaining pages before converting. If you have already partially iterated, the DataFrame will still include all records.

!!! tip
    DataFrame conversion requires `pip install kalshibook[pandas]`.

## Understanding Trade Records

Each trade record contains:

- **`yes_price` / `no_price`**: The price in cents for each side. These always sum to 100 (e.g., yes=65c, no=35c).
- **`count`**: Number of contracts in the trade.
- **`taker_side`**: Whether the taker (aggressor) was on the `"yes"` or `"no"` side.

## TradeRecord Fields

| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | `str` | Unique trade identifier |
| `market_ticker` | `str` | Market ticker |
| `yes_price` | `int` | Yes-side price in cents |
| `no_price` | `int` | No-side price in cents |
| `count` | `int` | Number of contracts |
| `taker_side` | `str` | Taker side (`"yes"` or `"no"`) |
| `ts` | `datetime` | Trade timestamp |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ticker` | `str` | required | Market ticker |
| `start_time` | `datetime` | required | Start of range (inclusive). Naive datetimes assumed UTC. |
| `end_time` | `datetime` | required | End of range (exclusive). Naive datetimes assumed UTC. |
| `limit` | `int` | `100` | Page size |
