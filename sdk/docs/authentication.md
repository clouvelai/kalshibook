# Authentication

This guide covers all methods for authenticating with the KalshiBook API, including best practices for keeping your credentials secure.

## API Key Format

KalshiBook API keys always start with the `kb-` prefix:

```
kb-a1b2c3d4e5f6...
```

Keys are generated from your [KalshiBook dashboard](https://kalshibook.io). Each key is tied to your account and metered for credit usage.

## Authentication Methods

### Direct Key

Pass your API key directly when constructing the client:

```python
from kalshibook import KalshiBook

client = KalshiBook(api_key="kb-your-api-key")
```

!!! warning "Avoid hardcoded keys"
    Passing keys directly is convenient for quick scripts, but avoid committing hardcoded keys to version control. Prefer environment variables for any shared or production code.

### Environment Variable

Set the `KALSHIBOOK_API_KEY` environment variable and use `from_env()`:

```bash
export KALSHIBOOK_API_KEY="kb-your-api-key"
```

```python
from kalshibook import KalshiBook

client = KalshiBook.from_env()
```

`from_env()` reads from the `KALSHIBOOK_API_KEY` environment variable. You can also pass additional keyword arguments:

```python
client = KalshiBook.from_env(timeout=60.0, max_retries=5)
```

!!! tip "Using .env files"
    For local development, store your key in a `.env` file:

    ```
    KALSHIBOOK_API_KEY=kb-your-api-key
    ```

    Load it with [python-dotenv](https://pypi.org/project/python-dotenv/) before creating the client:

    ```python
    from dotenv import load_dotenv
    from kalshibook import KalshiBook

    load_dotenv()
    client = KalshiBook.from_env()
    ```

### Constructor Without Explicit Key

If you omit `api_key`, the constructor also falls back to the `KALSHIBOOK_API_KEY` environment variable:

```python
# These are equivalent when KALSHIBOOK_API_KEY is set:
client = KalshiBook()
client = KalshiBook.from_env()
```

## Context Manager Usage

Use context managers for automatic transport cleanup:

=== "Sync"

    ```python
    from kalshibook import KalshiBook

    with KalshiBook("kb-your-api-key") as client:
        markets = client.list_markets()
        print(f"Found {len(markets.data)} markets")
    # Transport closed automatically
    ```

=== "Async"

    ```python
    import asyncio
    from kalshibook import KalshiBook

    async def main():
        async with KalshiBook("kb-your-api-key", sync=False) as client:
            markets = await client.alist_markets()
            print(f"Found {len(markets.data)} markets")
        # Transport closed automatically

    asyncio.run(main())
    ```

Without a context manager, call `close()` (sync) or `aclose()` (async) explicitly:

```python
client = KalshiBook("kb-your-api-key")
try:
    markets = client.list_markets()
finally:
    client.close()
```

## Sync vs Async Mode

By default, the client operates in synchronous mode. Set `sync=False` for async:

=== "Sync (default)"

    ```python
    client = KalshiBook("kb-your-api-key")  # sync=True is the default

    markets = client.list_markets()
    book = client.get_orderbook("TICKER", timestamp)
    ```

=== "Async"

    ```python
    client = KalshiBook("kb-your-api-key", sync=False)

    markets = await client.alist_markets()
    book = await client.aget_orderbook("TICKER", timestamp)
    ```

!!! note "Async method naming"
    All async methods use the `a` prefix: `alist_markets()`, `aget_orderbook()`, `alist_trades()`, etc.

## Client Options

The `KalshiBook` constructor accepts these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `None` | API key (falls back to env var) |
| `base_url` | `str` | `https://api.kalshibook.io` | API base URL |
| `sync` | `bool` | `True` | Use synchronous transport |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `max_retries` | `int` | `3` | Max retries for rate-limited requests |

## Credit Tracking

Every API response includes credit metadata in the `meta` field:

```python
response = client.list_markets()

print(f"Credits used: {response.meta.credits_used}")
print(f"Credits remaining: {response.meta.credits_remaining}")
print(f"Response time: {response.meta.response_time}s")
print(f"Request ID: {response.meta.request_id}")
```

Use this to monitor your credit consumption and implement usage-aware logic:

```python
from kalshibook import KalshiBook
from kalshibook.exceptions import CreditsExhaustedError

client = KalshiBook.from_env()

response = client.list_markets()
if response.meta.credits_remaining < 100:
    print("Warning: Running low on credits!")
```

## Error Handling

The SDK raises typed exceptions for authentication and billing errors:

```python
from kalshibook import KalshiBook
from kalshibook.exceptions import (
    AuthenticationError,
    CreditsExhaustedError,
    RateLimitError,
    MarketNotFoundError,
    ValidationError,
)

try:
    client = KalshiBook("kb-your-api-key")
    book = client.get_orderbook("KXBTC-25FEB14-T98250", timestamp)
except AuthenticationError as e:
    # Invalid or missing API key
    print(f"Auth failed: {e.message}")
    print(f"Status: {e.status_code}")
except CreditsExhaustedError:
    # Monthly credit limit reached -- not retryable
    print("Credits exhausted. Enable Pay-As-You-Go or upgrade your plan.")
except RateLimitError:
    # All retry attempts exhausted (SDK auto-retries 429s)
    print("Rate limited after max retries. Slow down requests.")
except MarketNotFoundError:
    # Ticker does not exist or has no data
    print("Market not found.")
except ValidationError as e:
    # Invalid parameters (e.g., bad timestamp format)
    print(f"Validation error: {e.message}")
```

!!! info "Auto-retry on rate limits"
    The SDK automatically retries rate-limited requests (HTTP 429) with exponential backoff and jitter. If a `Retry-After` header is present, it is honored. `RateLimitError` is only raised after all retry attempts are exhausted.

## Security Best Practices

1. **Never hardcode API keys** in source files that may be committed to version control
2. **Use environment variables** or `.env` files for key storage
3. **Add `.env` to `.gitignore`** to prevent accidental commits
4. **Rotate keys periodically** from the KalshiBook dashboard
5. **Use separate keys** for development and production environments
6. **Monitor credit usage** via `response.meta.credits_remaining` to detect unexpected consumption
