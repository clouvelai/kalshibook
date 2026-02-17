# Feature Research: Python SDK + Backtesting Abstractions

**Domain:** Python SDK wrapping a monetized prediction market L2 orderbook data API
**Researched:** 2026-02-17
**Confidence:** HIGH (patterns verified across Polygon, Databento, Alpaca, Tavily SDKs; KalshiBook API endpoints reviewed directly)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any Python data SDK. Missing these = SDK feels amateurish.

| Feature | Why Expected | Complexity | API Dependency | Notes |
|---------|--------------|------------|----------------|-------|
| **Typed client with API key init** | Every SDK (Polygon `RESTClient(api_key=)`, Tavily `TavilyClient(api_key=)`, Databento `Historical(api_key=)`, Alpaca `StockHistoricalDataClient(api_key, secret_key)`) initializes with an API key. Users also expect env var fallback (`KALSHIBOOK_API_KEY`). | LOW | All endpoints (X-API-Key header) | Use `httpx.Client` / `httpx.AsyncClient` internally. Accept key as arg or env var. Single `KalshiBook(api_key=)` entry point. |
| **Sync and async clients** | Polygon has `RESTClient`, Tavily has `TavilyClient` + `AsyncTavilyClient`, Databento has sync iterators + async iterators, Alpaca separates by data type. Quants use sync in notebooks, async in production bots. Both are required. | MEDIUM | All endpoints | Provide `KalshiBook()` (sync, uses `httpx.Client`) and `AsyncKalshiBook()` (async, uses `httpx.AsyncClient`). Mirror all methods. Polygon's approach of a single client class with sync methods is simpler to maintain than Alpaca's per-asset-class clients. |
| **Automatic pagination iteration** | Polygon's defining pattern: `for trade in client.list_trades("AAPL", "2023-01-04"): ...` -- the client handles cursor-based pagination behind the scenes, yielding individual records. Users never see cursors. KalshiBook's `/deltas` and `/trades` both use cursor-based pagination with `next_cursor` / `has_more`. | MEDIUM | POST /deltas (cursor pagination), POST /trades (cursor pagination) | Return lazy iterators that follow `next_cursor` automatically. Each call costs credits -- SDK handles pagination transparently but users should be aware of credit consumption. `limit` parameter controls page size, not total records. |
| **Pydantic response models** | Polygon returns typed model objects, Alpaca uses Pydantic for validation. Users expect `trade.yes_price` not `trade["yes_price"]`. Type hints enable IDE autocomplete and catch errors. Financial data users are precision-sensitive. | MEDIUM | All endpoints | Define Pydantic models mirroring API response shapes: `Orderbook`, `Delta`, `Trade`, `Candle`, `Market`, `Settlement`, `Event`. Reuse field names from existing API models. |
| **Context manager support** | httpx best practice: `with KalshiBook(api_key=) as client: ...` ensures connection pool cleanup. Polygon uses this, httpx documentation strongly recommends it. Connection reuse across calls reduces latency. | LOW | None (client-side pattern) | Implement `__enter__`/`__exit__` (sync) and `__aenter__`/`__aexit__` (async) that manage the underlying httpx client lifecycle. Also support non-context-manager usage for notebook convenience. |
| **Structured error handling** | Tavily raises `UsageLimitExceededError` (429), `InvalidAPIKeyError` (401), `BadRequestError` (400). Polygon doesn't do this well (users complain about opaque 429s). Good error hierarchy is table stakes for production use. KalshiBook API already returns structured `{error: {code, message, status}}` envelopes. | LOW | All endpoints (error responses) | Define exception hierarchy: `KalshiBookError` (base), `AuthenticationError` (401), `InsufficientCreditsError` (402/429), `ValidationError` (400/422), `NotFoundError` (404), `ServerError` (5xx). Parse API error envelope into typed exceptions. |
| **Retry with exponential backoff** | Polygon uses `urllib3.util.Retry` for 429/5xx. Financial data users run batch jobs that hit rate limits. SDK should handle transient failures transparently. Tavily notably does NOT retry, and users complain about it. | MEDIUM | All endpoints | Use `tenacity` for retry logic. Retry on 429 (rate limit) and 5xx (server errors) with exponential backoff + jitter. Respect `Retry-After` header if present. Make retry configurable: `KalshiBook(max_retries=3, backoff_factor=0.5)`. |
| **`.to_df()` / pandas conversion** | Databento: `data.to_df()`. Alpaca: `response.df` property returning multi-index DataFrame. This is the #1 pattern quants expect -- they live in pandas/jupyter. Every financial data SDK provides this. | MEDIUM | All list endpoints | Add `.to_df()` method on list response objects (trades, deltas, candles, markets, settlements). Return properly typed DataFrames with datetime index where appropriate. Make `pandas` an optional dependency (`pip install kalshibook[pandas]`). |

### Differentiators (Competitive Advantage)

Features that set KalshiBook's SDK apart from generic API wrappers.

| Feature | Value Proposition | Complexity | API Dependency | Notes |
|---------|-------------------|------------|----------------|-------|
| **`replay_orderbook()` -- historical orderbook reconstruction iterator** | Databento's killer feature is `data.replay(callback=handler)` for event-driven market replay. KalshiBook's core differentiator is point-in-time orderbook reconstruction. `replay_orderbook()` would iterate through time, yielding reconstructed orderbook state at each delta -- enabling users to "watch" how the orderbook evolved. No other Kalshi data provider offers this. | HIGH | POST /orderbook (reconstruction), POST /deltas (delta stream) | Two implementation approaches: (1) Server-side: call `/orderbook` at regular intervals (simple, expensive in credits), or (2) Client-side: fetch deltas via `/deltas`, reconstruct locally by applying deltas to initial snapshot (complex, credit-efficient). Recommend hybrid: fetch initial orderbook via `/orderbook`, then apply deltas client-side. Yield `OrderbookSnapshot` at each delta or at configurable intervals. This is the SDK's signature feature. |
| **`stream_trades()` -- historical trade replay** | Databento's replay pattern applied to trades. Users iterate trade history as if it were happening live: `for trade in client.stream_trades("TICKER", start, end): ...`. Useful for backtesting strategies against trade-by-trade execution data. | MEDIUM | POST /trades (paginated) | Build on auto-pagination iterator. Add time-based filtering, optional playback speed control (sleep between records to simulate real-time), and optional callback interface (like Databento's `replay(callback=)`). Simpler than orderbook replay because trades are flat records, no reconstruction needed. |
| **`get_orderbook()` single-call convenience** | Wraps POST /orderbook into `client.get_orderbook("TICKER", timestamp=datetime(...))`. Polygon has `client.get_aggs()` for single calls vs `client.list_aggs()` for iteration. The single-call pattern is the most common usage -- get the orderbook at one point in time. | LOW | POST /orderbook | Thin wrapper. Accept `datetime` objects (not ISO strings). Return typed `Orderbook` model with `.yes` and `.no` as lists of `Level(price=, quantity=)`. Include `.spread`, `.midpoint`, `.best_bid`, `.best_ask` computed properties. |
| **Market discovery helpers** | Polygon has `client.list_tickers()` with filtering. Users need to discover what markets exist, which have data, and for what time ranges. Current API has GET /markets and GET /events. | LOW | GET /markets, GET /events, GET /events/{ticker} | `client.list_markets(category=, status=)`, `client.get_market("TICKER")`, `client.list_events(category=, series_ticker=)`, `client.get_event("EVENT_TICKER")`. Return typed models with `first_data_at` / `last_data_at` so users know data coverage. |
| **`get_candles()` with DataFrame-first design** | OHLCV candles are the bread and butter of quant analysis. Existing GET /candles/{ticker} endpoint is perfect for SDK wrapping. Return as DataFrame by default since candles are inherently tabular. | LOW | GET /candles/{ticker} | `client.get_candles("TICKER", start, end, interval="1h")` returning `CandleResult` with `.to_df()`. DataFrame should have `bucket` as DatetimeIndex, columns for open/high/low/close/volume/trade_count. |
| **`get_settlement()` for P&L calculation** | Backtesting requires knowing final settlement values. `client.get_settlement("TICKER")` returns whether market resolved yes/no/void and at what value. Essential for computing strategy returns. | LOW | GET /settlements/{ticker}, GET /settlements | `client.get_settlement("TICKER")` and `client.list_settlements(event_ticker=)`. Enables `strategy_pnl = (settlement.value - entry_price) * contracts`. |
| **`backtest()` high-level orchestrator** | Combine replay_orderbook + stream_trades + settlements into a single backtesting workflow. User provides a strategy callback, SDK handles data fetching and P&L tracking. Inspired by Backtrader's integration with Alpaca, but purpose-built for prediction markets. | HIGH | All endpoints | This is a v2 feature. Requires replay_orderbook and stream_trades to be stable first. Define a `Strategy` protocol/ABC with `on_orderbook(snapshot)` and `on_trade(trade)` methods. SDK calls these in chronological order, tracks positions and P&L. |
| **Notebook-friendly repr** | Databento objects have rich `__repr__` in notebooks. Polygon objects print useful summaries. IPython/Jupyter users should see formatted output, not raw object dumps. | LOW | None (client-side) | Implement `_repr_html_()` for Jupyter rendering of orderbook snapshots (bid/ask table), trade lists, and candle data. Low effort, high perceived polish. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this SDK.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Caching layer in SDK** | "Don't re-fetch data I already have" -- seems efficient. Some SDKs like yfinance cache aggressively. | Prediction market data is already historical and immutable -- the API returns the same data for the same query. Adding caching in the SDK creates stale data bugs, memory bloat for large datasets, and cache invalidation complexity. The API layer already handles this (CDN/caching on the server side). Users who want caching can save DataFrames to parquet themselves. | Document the pattern: `df = client.get_candles(...).to_df(); df.to_parquet("candles.parquet")`. Let users manage their own data persistence. |
| **Built-in charting/visualization** | Alpaca's backtester blog posts show matplotlib charts. Users want `client.plot_orderbook()`. | Adds matplotlib/plotly as dependencies, bikeshed on chart styling, and different users want different visualization tools. SDK should produce data, not pictures. Twelve Data includes charting and it creates maintenance burden. | Return DataFrames that users can plot with their preferred tool. Provide example notebooks showing matplotlib/plotly usage. |
| **WebSocket real-time streaming** | "I want live data too, not just historical." Polygon and Alpaca both have WebSocket clients in their SDKs. | KalshiBook is a historical data product. Real-time data comes from Kalshi's own WebSocket (which is free and public). Wrapping Kalshi's live WebSocket in the KalshiBook SDK would be re-selling free data. It also requires fundamentally different infrastructure (persistent connections, heartbeats, reconnection logic). | Document how to use Kalshi's native WebSocket alongside KalshiBook historical data. Possibly provide a thin `KalshiLive` helper that connects to Kalshi directly (not through KalshiBook API), but keep it clearly separate from the data product. |
| **Auto-generated SDK from OpenAPI spec** | Tools like Fern, Speakeasy, and openapi-generator can auto-generate Python clients. Seems like zero effort. | Auto-generated SDKs are verbose, lack ergonomic methods (no `replay_orderbook()`), produce poor type names, and can't implement the client-side reconstruction logic that makes this SDK valuable. The backtesting abstractions ARE the product -- you can't auto-generate them. | Hand-craft the SDK with the backtesting abstractions as first-class features. Use OpenAPI spec as reference for endpoint shapes, but write the client manually. |
| **Async-only design** | "Modern Python should be async-first." Some newer SDKs only provide async interfaces. | Quants work in Jupyter notebooks where async is awkward (`await` in cells requires `nest_asyncio` hacks). Most backtesting happens in sync scripts. Databento and Polygon both offer sync interfaces because that's what data scientists use. Async-only alienates the primary user base. | Provide both sync and async. Sync is primary, async is available for production/bot use cases. Implement sync first, async mirrors sync API exactly. |
| **Strategy DSL / declarative backtesting** | Backtrader has a class-based strategy system. Users might want `@on_signal(...)` decorators or a custom language for defining strategies. | Massively increases scope, creates a framework lock-in, and competes with established backtesting frameworks (Backtrader, Zipline, vectorbt). KalshiBook should be a data provider, not a framework. | Provide raw data iterators and replay functions. Let users plug into their preferred backtesting framework. Offer example integrations with popular frameworks. |

## Feature Dependencies

```
Typed Client + API Key Init
    |
    +-- Structured Error Handling
    |       (errors need to be raised from client methods)
    |
    +-- Retry with Backoff
    |       (retry logic wraps client HTTP calls)
    |
    +-- Context Manager Support
    |       (manages underlying httpx client)
    |
    +-- Market Discovery Helpers
    |       (client.list_markets(), client.get_market())
    |       |
    |       +-- enhances --> Replay Orderbook
    |       |       (need to know data coverage before replaying)
    |       |
    |       +-- enhances --> Stream Trades
    |               (need to know data coverage before streaming)
    |
    +-- Auto-Pagination Iterator
    |       (core iteration pattern for /deltas and /trades)
    |       |
    |       +-- Stream Trades
    |       |       (paginated trade iteration with replay semantics)
    |       |
    |       +-- Replay Orderbook
    |               (fetches deltas via pagination, reconstructs client-side)
    |
    +-- Pydantic Response Models
    |       (all methods return typed objects)
    |       |
    |       +-- .to_df() / Pandas Conversion
    |       |       (convert typed models to DataFrames)
    |       |
    |       +-- Notebook-Friendly Repr
    |               (_repr_html_ on model objects)
    |
    +-- get_orderbook() Convenience
    |       (single-call wrapper, thin)
    |
    +-- get_candles() Convenience
    |       (single-call wrapper, thin)
    |
    +-- get_settlement() Convenience
            (single-call wrapper, thin)
            |
            +-- enhances --> backtest() Orchestrator
                    (needs settlement for P&L calculation)

Replay Orderbook + Stream Trades + get_settlement()
    |
    +-- backtest() High-Level Orchestrator (v2)
            (combines all three for end-to-end backtesting)
```

### Dependency Notes

- **Auto-pagination requires typed client:** Iterator logic lives in the base client, following cursors and yielding typed records.
- **Replay orderbook requires auto-pagination + response models:** Fetches deltas page-by-page, reconstructs orderbook using typed Delta/Orderbook models client-side.
- **Stream trades requires auto-pagination:** Thin layer over paginated /trades endpoint with optional replay timing.
- **`.to_df()` requires Pydantic models:** Conversion logic maps model fields to DataFrame columns.
- **`backtest()` requires replay + trades + settlements:** This is the capstone feature -- it cannot be built until the underlying data access methods are stable.
- **Market discovery enhances all replay features:** Users need to know what data exists (coverage dates) before they can meaningfully replay it.

## MVP Definition

### Launch With (v1.0)

Minimum viable SDK -- what's needed for users to prefer the SDK over raw HTTP calls.

- [x] `KalshiBook(api_key=)` typed client with env var fallback
- [x] Context manager support (`with KalshiBook() as client:`)
- [x] Structured exception hierarchy (AuthenticationError, InsufficientCreditsError, etc.)
- [x] Retry with exponential backoff on 429/5xx
- [x] `client.get_orderbook(ticker, timestamp, depth=)` -- single reconstruction call
- [x] `client.get_deltas(ticker, start, end)` -- auto-paginating iterator
- [x] `client.get_trades(ticker, start, end)` -- auto-paginating iterator
- [x] `client.get_candles(ticker, start, end, interval=)` -- candle data
- [x] `client.list_markets()`, `client.get_market(ticker)` -- discovery
- [x] `client.list_events()`, `client.get_event(event_ticker)` -- discovery
- [x] `client.get_settlement(ticker)`, `client.list_settlements()` -- settlement data
- [x] Pydantic response models for all endpoints
- [x] `.to_df()` on list results (pandas optional dependency)
- [x] Published to PyPI as `kalshibook`

### Add After Validation (v1.x)

Features to add once core SDK is in use and patterns are validated.

- [ ] `AsyncKalshiBook()` async client -- add when production bot users request it
- [ ] `replay_orderbook(ticker, start, end)` -- client-side orderbook reconstruction iterator
- [ ] `stream_trades(ticker, start, end, speed=)` -- trade replay with optional timing
- [ ] Notebook-friendly `_repr_html_()` -- add when Jupyter usage is confirmed
- [ ] Configurable `base_url` for self-hosted / staging environments

### Future Consideration (v2+)

Features to defer until SDK has proven adoption.

- [ ] `backtest()` orchestrator with Strategy protocol -- needs replay + settlements stable
- [ ] Backtrader / vectorbt integration adapters -- only if community requests
- [ ] CLI tool (`kalshibook fetch-candles TICKER ...`) -- only if non-programmatic use emerges

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Phase |
|---------|------------|---------------------|----------|-------|
| Typed client + API key init | HIGH | LOW | P1 | SDK Core |
| Context manager support | HIGH | LOW | P1 | SDK Core |
| Structured error handling | HIGH | LOW | P1 | SDK Core |
| Retry with backoff | HIGH | MEDIUM | P1 | SDK Core |
| Pydantic response models | HIGH | MEDIUM | P1 | SDK Core |
| get_orderbook() | HIGH | LOW | P1 | SDK Core |
| Auto-pagination (deltas, trades) | HIGH | MEDIUM | P1 | SDK Core |
| get_candles() | MEDIUM | LOW | P1 | SDK Core |
| list_markets() / get_market() | MEDIUM | LOW | P1 | SDK Core |
| list_events() / get_event() | MEDIUM | LOW | P1 | SDK Core |
| get_settlement() / list_settlements() | MEDIUM | LOW | P1 | SDK Core |
| .to_df() pandas conversion | HIGH | MEDIUM | P1 | SDK Core |
| PyPI publishing | HIGH | LOW | P1 | SDK Core |
| Async client (AsyncKalshiBook) | MEDIUM | MEDIUM | P2 | Post-core |
| replay_orderbook() | HIGH | HIGH | P2 | Backtesting |
| stream_trades() | MEDIUM | MEDIUM | P2 | Backtesting |
| Notebook repr | LOW | LOW | P2 | Polish |
| backtest() orchestrator | MEDIUM | HIGH | P3 | v2 |

## Competitor Feature Analysis

| Feature | Polygon (polygon-api-client) | Databento (databento-python) | Alpaca (alpaca-py) | Tavily (tavily-python) | KalshiBook SDK (planned) |
|---------|------------------------------|-------------------------------|--------------------|-----------------------|--------------------------|
| **Client init** | `RESTClient(api_key=)` | `Historical(api_key=)`, env var fallback | Per-asset-class clients | `TavilyClient(api_key=)`, env var fallback | `KalshiBook(api_key=)`, env var fallback |
| **Sync/Async** | Sync only (REST), async for WS | Sync iterators + async iterators | Separate sync clients per asset | Sync + `AsyncTavilyClient` | Sync primary, `AsyncKalshiBook` in v1.x |
| **Auto-pagination** | Yes, default on. `for t in client.list_trades(): ...` | N/A (batch downloads) | Not documented | N/A (single-call API) | Yes, for /deltas and /trades |
| **Response types** | Typed model objects | `DBNStore` with record iteration | Pydantic models | Dict | Pydantic models |
| **DataFrame support** | No built-in .to_df() | `data.to_df()`, `data.to_ndarray()` | `.df` property (multi-index) | No | `.to_df()` on all list results |
| **Data replay** | No | `data.replay(callback=)` | No | No | `replay_orderbook()`, `stream_trades()` |
| **Error handling** | Poor (opaque HTTP errors, users complain about 429s) | Not documented | Not documented | Typed exceptions (429, 401, 400, 403) | Typed exception hierarchy |
| **Retry/backoff** | `urllib3.util.Retry` built-in (429, 5xx) | Not documented | Not documented | None | `tenacity`-based, configurable |
| **Market discovery** | `client.list_tickers()` with filtering | Metadata API | Per-asset listing | N/A | `list_markets()`, `list_events()` |
| **Custom JSON parser** | Yes (`custom_json` param, orjson support) | Custom binary format (DBN) | No | No | orjson default (matches API server) |

### Key Takeaways from Competitor Analysis

1. **Polygon's auto-pagination is the gold standard** for iterator-based data access. Copy this pattern exactly for /deltas and /trades.
2. **Databento's replay() is the gold standard** for event-driven historical data processing. Adapt this pattern for `replay_orderbook()`.
3. **Alpaca's per-asset-class client split is unnecessarily complex** for KalshiBook's simpler API surface. Use a single client class.
4. **Tavily's error handling is best-in-class** among these SDKs -- specific exception types for each error category. Polygon's lack of error handling is a known pain point.
5. **DataFrame conversion is expected** by financial data users. Databento and Alpaca both provide it. Polygon's lack of it is notable.
6. **Nobody provides both replay AND auto-pagination AND typed errors.** There is an opportunity to be best-in-class across all three dimensions simultaneously.

## Sources

### Primary (HIGH confidence -- reviewed source code / official docs)
- [Polygon.io Python Client (GitHub)](https://github.com/polygon-io/client-python) -- pagination pattern, RESTClient architecture, retry configuration
- [Polygon Advanced Usage (DeepWiki)](https://deepwiki.com/polygon-io/client-python/7-advanced-usage) -- pagination internals, error handling strategies, custom JSON
- [Tavily Python Client (GitHub)](https://github.com/tavily-ai/tavily-python) -- error handling hierarchy, client init pattern, sync/async split
- [Databento Python Client (GitHub)](https://github.com/databento/databento-python) -- replay() pattern, DataFrame conversion, Historical client
- [Alpaca-py (GitHub)](https://github.com/alpacahq/alpaca-py) -- request object pattern, per-asset clients, Pydantic usage
- [HTTPX Async Docs](https://www.python-httpx.org/async/) -- AsyncClient context manager, connection pooling
- KalshiBook API source code (reviewed directly) -- endpoint shapes, pagination cursors, response models

### Secondary (MEDIUM confidence -- multiple sources agree)
- [Databento Example Use Cases (DeepWiki)](https://deepwiki.com/databento/databento-python/7-example-use-cases) -- replay and iterator patterns
- [Tenacity retry library (GitHub)](https://github.com/jd/tenacity) -- retry/backoff patterns for Python SDKs
- [Alpaca Market Data Docs](https://alpaca.markets/sdks/python/market_data.html) -- historical data client patterns

### Tertiary (LOW confidence -- needs validation)
- DataFrame integration patterns from blog posts -- specific column naming conventions may vary

---
*Feature research for: Python SDK + Backtesting Abstractions (KalshiBook)*
*Researched: 2026-02-17*
