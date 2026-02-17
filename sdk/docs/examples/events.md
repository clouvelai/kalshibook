# Events

Browse events and their child markets. Events are the top-level grouping on Kalshi -- each event contains one or more individual markets.

## Understanding the Hierarchy

Kalshi organizes data in a hierarchy:

```
Series (e.g., "Bitcoin Price")
  └── Event (e.g., "BTC Price on Feb 14, 2025")
        ├── Market (e.g., "BTC above $98,250")
        ├── Market (e.g., "BTC above $99,000")
        └── Market (e.g., "BTC above $100,000")
```

KalshiBook tracks this hierarchy so you can discover related markets.

## List Events

`list_events()` returns a summary of all tracked events:

```python
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

events = client.list_events()

for event in events.data:
    print(f"{event.event_ticker}: {event.title} ({event.market_count} markets)")
```

## Filter Events

Use optional parameters to narrow results:

```python
# Filter by category
crypto_events = client.list_events(category="crypto")

# Filter by series
btc_events = client.list_events(series_ticker="KXBTC")

# Filter by status
open_events = client.list_events(status="open")

# Combine filters
open_crypto = client.list_events(category="crypto", status="open")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | `str \| None` | Filter by category slug |
| `series_ticker` | `str \| None` | Filter by parent series ticker |
| `status` | `str \| None` | Filter by event status (`"open"`, `"closed"`) |

## Get Event Detail

`get_event()` returns full detail for a single event, including its child markets:

```python
event_detail = client.get_event("KXBTC-25FEB14")

event = event_detail.data
print(f"Event: {event.title}")
print(f"Category: {event.category}")
print(f"Status: {event.status}")
print(f"Mutually exclusive: {event.mutually_exclusive}")
print(f"Markets: {event.market_count}")

# List all child markets
for market in event.markets:
    print(f"  {market.ticker}: {market.title} [{market.status}]")
```

## Convert to DataFrame

```python
events = client.list_events()
df = events.to_df()

print(df[["event_ticker", "title", "category", "status", "market_count"]])
```

!!! tip
    DataFrame conversion requires `pip install kalshibook[pandas]`.

## EventSummary Fields

Returned by `list_events()`:

| Field | Type | Description |
|-------|------|-------------|
| `event_ticker` | `str` | Event ticker |
| `series_ticker` | `str \| None` | Parent series ticker |
| `title` | `str \| None` | Event title |
| `sub_title` | `str \| None` | Event subtitle |
| `category` | `str \| None` | Category slug |
| `mutually_exclusive` | `bool \| None` | Whether markets are mutually exclusive |
| `status` | `str \| None` | Event status |
| `market_count` | `int \| None` | Number of child markets |

## EventDetail Fields

Returned by `get_event()` -- includes all EventSummary fields plus:

| Field | Type | Description |
|-------|------|-------------|
| `markets` | `list[MarketSummary]` | Child markets belonging to this event |
