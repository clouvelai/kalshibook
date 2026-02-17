# Candles

Retrieve OHLCV (Open, High, Low, Close, Volume) candlestick data for any market over a time range.

## Basic Usage

```python
from datetime import datetime, timezone
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

candles = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=datetime(2025, 2, 13, 0, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 2, 14, 0, 0, tzinfo=timezone.utc),
    interval="1h",
)

for candle in candles.data:
    print(
        f"{candle.bucket}: "
        f"O={candle.open} H={candle.high} L={candle.low} C={candle.close} "
        f"V={candle.volume} trades={candle.trade_count}"
    )
```

## Interval Options

The `interval` parameter controls the candle width. Common values:

| Interval | Description |
|----------|-------------|
| `"1m"` | 1 minute |
| `"5m"` | 5 minutes |
| `"15m"` | 15 minutes |
| `"1h"` | 1 hour |
| `"4h"` | 4 hours |
| `"1d"` | 1 day |

The server validates interval values, so new intervals may be added without SDK updates.

```python
# Hourly candles (default)
hourly = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=start,
    end_time=end,
    interval="1h",
)

# 1-minute candles for high-resolution analysis
minute = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=start,
    end_time=end,
    interval="1m",
)
```

## Convert to DataFrame

Candle data is naturally tabular, making DataFrame conversion especially useful:

```python
candles = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=datetime(2025, 2, 13, 0, 0, tzinfo=timezone.utc),
    end_time=datetime(2025, 2, 14, 0, 0, tzinfo=timezone.utc),
    interval="1h",
)

df = candles.to_df()
print(df[["bucket", "open", "high", "low", "close", "volume"]])
```

!!! tip
    DataFrame conversion requires `pip install kalshibook[pandas]`.

## CandleRecord Fields

| Field | Type | Description |
|-------|------|-------------|
| `bucket` | `datetime` | Start of the candle period |
| `market_ticker` | `str` | Market ticker |
| `open` | `int` | Opening price (cents) |
| `high` | `int` | Highest price (cents) |
| `low` | `int` | Lowest price (cents) |
| `close` | `int` | Closing price (cents) |
| `volume` | `int` | Number of contracts traded |
| `trade_count` | `int` | Number of individual trades |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ticker` | `str` | required | Market ticker |
| `start_time` | `datetime` | required | Start of range (inclusive). Naive datetimes assumed UTC. |
| `end_time` | `datetime` | required | End of range (exclusive). Naive datetimes assumed UTC. |
| `interval` | `str` | `"1h"` | Candle width |
