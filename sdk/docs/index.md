# KalshiBook Python SDK

L2 orderbook data for Kalshi prediction markets.

---

KalshiBook provides a typed Python SDK for accessing historical and real-time
orderbook data on Kalshi prediction markets. Query orderbook snapshots, trades,
OHLCV candles, market metadata, event hierarchies, and settlement records
through a simple, well-documented API.

## Features

- **Typed responses** -- All API responses are frozen dataclasses with full type annotations
- **Sync and async** -- Use `KalshiBook(api_key, sync=True)` or `sync=False` for async workflows
- **Auto-pagination** -- `PageIterator` handles multi-page results transparently
- **DataFrame support** -- Call `.to_df()` on any response or paginated iterator to get a pandas DataFrame
- **Comprehensive error handling** -- Typed exceptions for auth errors, rate limits, and missing data

## Installation

=== "Standard"

    ```bash
    pip install kalshibook
    ```

=== "With pandas support"

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
    print(f"  YES {level.price}c  x{level.quantity}")

# List available markets as a DataFrame
markets = client.list_markets()
df = markets.to_df()
print(df[["ticker", "title", "status"]])

client.close()
```

## Next Steps

- [Getting Started](getting-started.md) -- Full setup and first queries
- [Authentication](authentication.md) -- API key configuration and environment variables
- [API Reference](reference/) -- Complete SDK reference generated from source
