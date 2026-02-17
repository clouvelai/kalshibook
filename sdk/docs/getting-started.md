# Getting Started

This guide walks you through installing KalshiBook, configuring your API key, and making your first queries.

## Installation

=== "Standard"

    ```bash
    pip install kalshibook
    ```

=== "With pandas support"

    ```bash
    pip install kalshibook[pandas]
    ```

!!! tip "pandas is optional"
    The `[pandas]` extra installs pandas for `.to_df()` support on responses.
    The core SDK has no dependency on pandas -- you only need it if you want DataFrame conversion.

## Get an API Key

1. Sign up at [kalshibook.io](https://kalshibook.io)
2. Navigate to your dashboard and generate an API key
3. Your key will start with `kb-` -- keep it secret

!!! warning "Keep your key safe"
    Never commit API keys to source control. Use environment variables or `.env` files instead.
    See the [Authentication guide](authentication.md) for best practices.

## Your First Query

Create a client and fetch an orderbook snapshot:

=== "Sync"

    ```python
    from datetime import datetime, timezone
    from kalshibook import KalshiBook

    client = KalshiBook("kb-your-api-key")

    # Reconstruct the orderbook at a specific point in time
    book = client.get_orderbook(
        "KXBTC-25FEB14-T98250",
        timestamp=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
    )

    print(f"Market: {book.market_ticker}")
    print(f"Snapshot basis: {book.snapshot_basis}")
    print(f"Deltas applied: {book.deltas_applied}")

    # Print top 5 Yes levels
    for level in book.yes[:5]:
        print(f"  YES {level.price}c  x{level.quantity}")

    # Print top 5 No levels
    for level in book.no[:5]:
        print(f"  NO  {level.price}c  x{level.quantity}")

    client.close()
    ```

=== "Async"

    ```python
    import asyncio
    from datetime import datetime, timezone
    from kalshibook import KalshiBook

    async def main():
        client = KalshiBook("kb-your-api-key", sync=False)

        book = await client.aget_orderbook(
            "KXBTC-25FEB14-T98250",
            timestamp=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
        )

        print(f"Market: {book.market_ticker}")
        for level in book.yes[:5]:
            print(f"  YES {level.price}c  x{level.quantity}")

        await client.aclose()

    asyncio.run(main())
    ```

## List Available Markets

Browse all markets tracked by KalshiBook:

```python
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

markets = client.list_markets()

for market in markets.data:
    print(f"{market.ticker}: {market.title} [{market.status}]")

client.close()
```

## Convert to DataFrame

Any list response supports `.to_df()` for conversion to a pandas DataFrame:

```python
from kalshibook import KalshiBook

client = KalshiBook("kb-your-api-key")

markets = client.list_markets()
df = markets.to_df()

print(df[["ticker", "title", "status"]].head(10))
```

!!! tip "Install pandas first"
    DataFrame support requires the pandas extra:
    ```bash
    pip install kalshibook[pandas]
    ```

## Using a Context Manager

The client supports context manager syntax for automatic cleanup:

```python
from datetime import datetime, timezone
from kalshibook import KalshiBook

with KalshiBook("kb-your-api-key") as client:
    book = client.get_orderbook(
        "KXBTC-25FEB14-T98250",
        timestamp=datetime(2025, 2, 14, 12, 0, tzinfo=timezone.utc),
    )
    print(f"Yes levels: {len(book.yes)}, No levels: {len(book.no)}")
# Transport is automatically closed here
```

## Credit Tracking

Every response includes metadata about credit usage:

```python
markets = client.list_markets()

print(f"Credits used: {markets.meta.credits_used}")
print(f"Credits remaining: {markets.meta.credits_remaining}")
```

## Next Steps

- [Authentication](authentication.md) -- API key configuration, environment variables, and security best practices
- [Examples](examples/orderbook.md) -- Complete code examples for every endpoint
- [API Reference](reference/) -- Full SDK reference generated from source
