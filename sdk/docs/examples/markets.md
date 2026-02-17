# Markets

Browse available markets and retrieve detailed information for individual markets.

## List All Markets

`list_markets()` returns a summary of every market tracked by KalshiBook:

```python
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

markets = client.list_markets()

for market in markets.data:
    print(f"{market.ticker}: {market.title} [{market.status}]")
```

## Get Market Detail

`get_market()` returns full detail for a single market, including data coverage statistics:

```python
detail = client.get_market("KXBTC-25FEB14-T98250")

market = detail.data
print(f"Ticker: {market.ticker}")
print(f"Title: {market.title}")
print(f"Event: {market.event_ticker}")
print(f"Status: {market.status}")
print(f"Category: {market.category}")
print(f"Rules: {market.rules}")
print(f"Strike price: {market.strike_price}")
print(f"Data from: {market.first_data_at} to {market.last_data_at}")
print(f"Snapshots: {market.snapshot_count}")
print(f"Deltas: {market.delta_count}")
```

## MarketSummary vs MarketDetail

`list_markets()` returns `MarketSummary` objects with basic fields. `get_market()` returns a `MarketDetail` with additional fields:

| Field | MarketSummary | MarketDetail |
|-------|:---:|:---:|
| `ticker` | Yes | Yes |
| `title` | Yes | Yes |
| `event_ticker` | Yes | Yes |
| `status` | Yes | Yes |
| `category` | Yes | Yes |
| `first_data_at` | Yes | Yes |
| `last_data_at` | Yes | Yes |
| `rules` | -- | Yes |
| `strike_price` | -- | Yes |
| `discovered_at` | -- | Yes |
| `metadata` | -- | Yes |
| `snapshot_count` | -- | Yes |
| `delta_count` | -- | Yes |

## Filter by Status

Use `get_market()` detail to inspect market status, then filter programmatically:

```python
markets = client.list_markets()

open_markets = [m for m in markets.data if m.status == "open"]
print(f"Open markets: {len(open_markets)}")

for market in open_markets[:5]:
    print(f"  {market.ticker}: {market.title}")
```

## Convert to DataFrame

```python
markets = client.list_markets()
df = markets.to_df()

print(df[["ticker", "title", "status", "category"]].head(10))
```

!!! tip
    DataFrame conversion requires `pip install kalshibook[pandas]`.

## MarketSummary Fields

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | `str` | Market ticker |
| `title` | `str \| None` | Human-readable market title |
| `event_ticker` | `str \| None` | Parent event ticker |
| `status` | `str` | Market status (`"open"`, `"closed"`, etc.) |
| `category` | `str \| None` | Category slug |
| `first_data_at` | `datetime \| None` | Earliest captured data timestamp |
| `last_data_at` | `datetime \| None` | Most recent captured data timestamp |
