# DataFrames

Convert any list response or paginated result to a pandas DataFrame with `.to_df()`.

## Setup

DataFrame support requires the `pandas` extra:

```bash
pip install kalshibook[pandas]
```

## List Responses

All list responses (`MarketsResponse`, `CandlesResponse`, `EventsResponse`, `SettlementsResponse`) support `.to_df()`:

```python
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

# Markets
markets_df = client.list_markets().to_df()
print(markets_df[["ticker", "title", "status"]].head())

# Events
events_df = client.list_events().to_df()
print(events_df[["event_ticker", "title", "category"]].head())

# Settlements
settlements_df = client.list_settlements().to_df()
print(settlements_df[["market_ticker", "result", "settled_at"]].head())
```

## Candle DataFrames

Candle data is naturally tabular -- ideal for time series analysis:

```python
from datetime import datetime, timezone

candles_df = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=datetime(2025, 2, 13, 0, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 2, 14, 0, 0, tzinfo=timezone.utc),
    interval="1h",
).to_df()

print(candles_df[["bucket", "open", "high", "low", "close", "volume"]])
```

## Paginated Results

`PageIterator` (returned by `list_deltas()` and `list_trades()`) also supports `.to_df()`. It drains all remaining pages before converting:

```python
# All deltas as a DataFrame
deltas_df = client.list_deltas(
    "KXBTC-25FEB14-T98250",
    start_time=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 2, 14, 13, 0, tzinfo=timezone.utc),
).to_df()

print(f"Total deltas: {len(deltas_df)}")
print(deltas_df.head())

# All trades as a DataFrame
trades_df = client.list_trades(
    "KXBTC-25FEB14-T98250",
    start_time=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 2, 14, 13, 0, tzinfo=timezone.utc),
).to_df()

print(f"Total trades: {len(trades_df)}")
print(trades_df.head())
```

!!! note "Pagination is handled automatically"
    `.to_df()` fetches all remaining pages before building the DataFrame. If you have already partially iterated through the `PageIterator`, the DataFrame will still contain all records (both previously yielded and remaining).

## Pandas Operations

Once you have a DataFrame, use standard pandas for analysis:

### Filtering

```python
markets_df = client.list_markets().to_df()

# Only open markets
open_markets = markets_df[markets_df["status"] == "open"]
print(f"Open markets: {len(open_markets)}")

# Markets in a specific category
crypto = markets_df[markets_df["category"] == "crypto"]
```

### Grouping

```python
# Trades by taker side
trades_df = client.list_trades(
    "KXBTC-25FEB14-T98250", start, end
).to_df()

by_side = trades_df.groupby("taker_side").agg(
    trades=("trade_id", "count"),
    volume=("count", "sum"),
)
print(by_side)
```

### Time Series

```python
# Set bucket as index for time series operations
candles_df = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=start,
    end_time=end,
    interval="1h",
).to_df()

candles_df = candles_df.set_index("bucket")
print(candles_df["close"].describe())
```

### Sorting

```python
# Sort settlements by settlement time
settlements_df = client.list_settlements().to_df()
sorted_df = settlements_df.sort_values("settled_at", ascending=False)
print(sorted_df.head())
```

## Without pandas

If pandas is not installed, calling `.to_df()` raises an `ImportError` with installation instructions:

```python
try:
    df = client.list_markets().to_df()
except ImportError as e:
    print(e)  # "pandas is required for .to_df(). Install with: pip install kalshibook[pandas]"
```

You can always work with the raw dataclass objects without pandas:

```python
markets = client.list_markets()
for market in markets.data:
    print(f"{market.ticker}: {market.title}")
```
