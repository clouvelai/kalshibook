# KalshiBook

[![PyPI version](https://img.shields.io/pypi/v/kalshibook.svg)](https://pypi.org/project/kalshibook/)
[![Python versions](https://img.shields.io/pypi/pyversions/kalshibook.svg)](https://pypi.org/project/kalshibook/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Python SDK for the KalshiBook L2 orderbook data API. Query historical orderbook snapshots, trades, OHLCV candles, market metadata, event hierarchies, and settlement records for Kalshi prediction markets.

## Installation

```bash
pip install kalshibook
```

With optional pandas support for `.to_df()` conversion:

```bash
pip install kalshibook[pandas]
```

## Quick Start

```python
from datetime import datetime, timezone
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

# Reconstruct an orderbook at a point in time
book = client.get_orderbook(
    "KXBTC-25FEB14-T98250",
    timestamp=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
)
for level in book.yes[:5]:
    print(f"YES {level.price}c x{level.quantity}")

client.close()
```

## Key Features

- **Typed responses** -- All API responses are frozen dataclasses with full type annotations
- **Sync and async** -- Use `KalshiBook(api_key, sync=True)` or `sync=False` for async workflows
- **Auto-pagination** -- `PageIterator` handles multi-page results transparently for deltas and trades
- **DataFrame support** -- Call `.to_df()` on any list response or paginated iterator
- **Comprehensive errors** -- Typed exceptions for auth, rate limits, credits, and missing data
- **Auto-retry** -- Rate-limited requests are retried with exponential backoff and jitter

## Usage Examples

### List markets

```python
markets = client.list_markets()
for m in markets.data:
    print(f"{m.ticker}: {m.title}")
```

### OHLCV candles

```python
candles = client.get_candles(
    "KXBTC-25FEB14-T98250",
    start_time=start,
    end_time=end,
    interval="1h",
)
df = candles.to_df()  # requires kalshibook[pandas]
```

### Paginated trades

```python
for trade in client.list_trades("KXBTC-25FEB14-T98250", start, end):
    print(f"{trade.yes_price}c x{trade.count}")
```

### Async

```python
async with KalshiBook("kb-your-api-key", sync=False) as client:
    markets = await client.alist_markets()
```

## Documentation

Full documentation with guides, examples, and API reference:

**[kalshibook.github.io/kalshibook](https://kalshibook.github.io/kalshibook/)**

- [Getting Started](https://kalshibook.github.io/kalshibook/getting-started/) -- Installation, first queries, DataFrames
- [Authentication](https://kalshibook.github.io/kalshibook/authentication/) -- API keys, environment variables, error handling
- [API Reference](https://kalshibook.github.io/kalshibook/reference/) -- Complete SDK reference from source

## License

MIT
