# Feature Research

**Domain:** Monetized prediction market L2 orderbook data API
**Researched:** 2026-02-13
**Confidence:** MEDIUM (training data + web research; no direct user interviews)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **REST API for historical orderbook snapshots** | Every market data API (Polygon, Databento, Alpaca) exposes historical data via REST. Algo traders and quants need point-in-time orderbook state for backtesting. This is the core product. | HIGH | Requires orderbook reconstruction engine: initial snapshot + ordered deltas to rebuild state at arbitrary timestamp. Databento solves this with MBO snapshots generated every minute; Tardis.dev stores raw exchange messages and replays them. KalshiBook must reconstruct from stored snapshots + deltas. |
| **API key authentication** | Universal across all monetized APIs (Polygon, Databento, Tavily, Exa). No API ships without key-based auth. Bearer token or API key header. | LOW | Standard pattern. Kalshi's own API uses API key in headers. Supabase Auth + RLS can handle this with a custom API keys table. |
| **Rate limiting with response headers** | Industry standard. Polygon has 5 calls/min on free, unlimited on paid. Tavily uses credit-based limits. Exa uses QPS limits. Users expect `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers. | MEDIUM | Needs middleware that checks tier, tracks usage, returns headers. Must be per-key, not per-IP. |
| **Tiered pricing (free tier through paid)** | Tavily: free 1,000 credits/mo, PAYG $0.008/credit, Project $30/mo, Enterprise custom. Polygon: free 5 calls/min, Starter $29/mo, Developer $79/mo, Advanced $200/mo. Databento: $125 free credit, then usage-based. Free tier is mandatory for adoption. | MEDIUM | Stripe subscription management. Four tiers: Free, Pay-As-You-Go, Project, Enterprise. Credit-based like Tavily (each API call costs credits). |
| **Market metadata endpoint** | All market data APIs include instrument/symbol metadata. Kalshi markets have event info, contract specs, expiration dates, settlement rules. Users need this to know what they're looking at. | LOW | Kalshi's own API already provides this. Mirror/cache it and expose through KalshiBook API. |
| **JSON response format** | Every modern API returns JSON. Polygon, Databento, Alpaca, Tavily, Exa all use JSON. Non-negotiable. | LOW | FastAPI handles this natively. |
| **Consistent error responses** | Agent-friendly APIs need structured errors with `error_code`, `message`, `type` fields. AI agents parse these programmatically. Inconsistent errors break agent workflows. | LOW | Define a standard error envelope. Return it for all 4xx/5xx responses. |
| **API documentation (OpenAPI spec)** | Polygon publishes full OpenAPI specs. Databento has comprehensive docs. Tavily documents every endpoint with examples. Plaid auto-generates SDKs from OpenAPI. Without docs, no one integrates. | MEDIUM | OpenAPI 3.1 spec auto-generated from FastAPI. Include descriptions, examples, and parameter details. Publish at `/openapi.json`. |
| **Usage tracking / dashboard** | Users need to see how many credits they've used, current billing period, remaining quota. Tavily, Polygon, and Exa all provide this. | MEDIUM | Web dashboard showing: API key management, usage graphs, billing info. Supabase + simple frontend. |
| **Real-time websocket streaming** | Alpaca, Polygon, and Databento all offer websocket streaming for real-time data. Kalshi itself exposes orderbook via websocket. Live traders need real-time feeds. | HIGH | Re-broadcast collected websocket data to subscribers. Needs connection management, subscription handling, authentication on WS connect. Supabase Realtime could help but may need custom WS server for performance. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Point-in-time orderbook reconstruction** | Tardis.dev's core value prop for crypto. No one does this for Kalshi. Quants need "what did the orderbook look like at exactly 2:34:17 PM on election day?" for backtesting. Databento generates MBO snapshots every minute; Tardis.dev replays raw messages. KalshiBook can reconstruct to arbitrary timestamps. | HIGH | Core differentiator. Build reconstruction engine that takes a base snapshot + applies deltas up to target timestamp. Must be fast enough for bulk backtesting queries. Depends on: complete data collection, ordered delta storage. |
| **Raw delta stream access** | Tardis.dev provides raw exchange-native messages. Advanced quants and HFT-style traders want raw deltas, not reconstructed state. They build their own orderbook models. | MEDIUM | Expose stored deltas as a paginated stream endpoint. Time-range queries. Already storing the data — just need an API layer. Lower complexity than reconstruction but very high value for sophisticated users. |
| **Agent-friendly API design (Tavily-style)** | Tavily's success comes from being the default search API for AI agents. KalshiBook targeting the same: AI trading bots (Claude, GPT-based) that need structured market data. Self-describing endpoints, LLM-optimized response shapes, natural language field names. | MEDIUM | Design principles from research: (1) Self-describing OpenAPI spec with natural language descriptions, (2) Flat JSON structures (avoid deep nesting), (3) Consistent naming across endpoints, (4) Include contextual metadata in responses (not just raw numbers), (5) Deterministic response shapes. |
| **MCP server** | Model Context Protocol is the emerging standard for AI agent tool use. Polygon.io, Alpha Vantage, and Polymarket already have MCP servers. Kalshi has community MCP servers but no official orderbook data MCP. Being the canonical Kalshi orderbook MCP server is a land-grab opportunity. | MEDIUM | Implement MCP server that exposes KalshiBook endpoints as tools. Agents can query orderbook state, get market metadata, stream updates through MCP. FastAPI endpoints become MCP tools. Growing ecosystem — early mover advantage. |
| **Downloadable flat files (CSV/Parquet)** | Tardis.dev offers downloadable CSV datasets. Databento offers batch downloads in binary/CSV. Quants doing large-scale backtesting want to download entire datasets, not make thousands of API calls. | MEDIUM | Generate daily/weekly snapshots as CSV or Parquet files. Host on S3-compatible storage (Supabase Storage). Reduces API load for bulk users. Can be a premium tier feature. |
| **Credit-based pricing with transparent costs** | Tavily's credit system is elegant: basic search = 1 credit, advanced = 2 credits. Users know exactly what each call costs. No surprise bills. Agent-friendly because bots can budget programmatically. | LOW | Define credit costs per endpoint: snapshot query = 1 credit, reconstruction = 2 credits, bulk download = N credits. Transparent, predictable, machine-budgetable. |
| **`/llms.txt` and `/llms-full.txt` discovery** | Emerging convention (Kalshi itself publishes `docs.kalshi.com/llms.txt`). AI agents and LLMs look for these files to understand API capabilities without reading full docs. Early signal of agent-first thinking. | LOW | Static text files describing API capabilities in LLM-friendly format. Minimal effort, strong signal to agent builders that this API is built for them. |
| **Python SDK** | Databento's Python client is excellent: supports DataFrames, replay, normalized schemas. Tardis.dev has Node.js and Python clients. Algo traders overwhelmingly use Python. | MEDIUM | Auto-generate from OpenAPI spec (tools like Fern, APIMatic). Add convenience methods for common workflows: `client.get_orderbook(ticker, timestamp)`, `client.stream(tickers)`. Publish to PyPI. |
| **Sequence numbers for delta ordering** | Databento and exchange APIs use sequence numbers to detect gaps. Essential for data integrity — if a subscriber misses delta #47, they know to re-snapshot. Without this, orderbook reconstruction is unreliable. | LOW | Add monotonically increasing sequence number to each delta. Include in both stored data and streamed output. Enables gap detection and reliable replay. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **OHLCV candle aggregation** | Traditional market data APIs (Polygon, Alpaca) all have candle/bar endpoints. Seems like table stakes. | Prediction markets are fundamentally different from equities. Binary outcomes, 0-100 cent price range, event-driven (not continuous trading sessions). OHLCV candles obscure the orderbook dynamics that are KalshiBook's actual value. Building candle aggregation is moderate complexity and distracts from the core differentiator. Also, Kalshi's own API already provides basic price data — competing on candles is a losing game. | Expose raw orderbook data and let users compute their own aggregations. Possibly add as a v2+ feature if demand is validated. PROJECT.md already marks this as out of scope. |
| **Trade execution / order placement** | Users trading on Kalshi will want to place orders through the same API they get data from. "One API for everything." | Turns a read-only data product into a brokerage. Regulatory complexity (CFTC-regulated exchange), liability, Kalshi API ToS issues, massive security surface area. Completely different product. | Stay read-only. Document how to use KalshiBook data alongside Kalshi's own trading API. Provide clear links to Kalshi's trading docs. PROJECT.md already excludes this. |
| **Multi-exchange aggregation** | FinFeedAPI aggregates Kalshi + Polymarket + Manifold. Seems like a bigger TAM. | Polymarket is crypto/blockchain-based (different data model entirely). Manifold is play money. Aggregating across incompatible market structures creates a lowest-common-denominator product. KalshiBook's value is depth on Kalshi, not breadth across platforms. Also massively increases engineering scope. | Go deep on Kalshi. If demand exists, add Polymarket as a separate data source in a future milestone, not a unified schema. |
| **Real-time analytics / derived metrics** | Sophisticated metrics like order flow imbalance, VWAP, bid-ask spread timeseries, market impact estimates. | Each metric is a mini-product with its own correctness requirements, edge cases, and maintenance burden. Premature optimization of the data layer before validating core demand. Users who need these can compute them from raw data. | Provide raw data with enough fidelity that users can compute any derived metric. Consider adding 2-3 high-value derived metrics (e.g., mid-price, spread) in v2 after validating demand. |
| **GraphQL API** | Some developers prefer GraphQL for flexible queries. | Adds a second API surface to maintain. Market data APIs overwhelmingly use REST (Polygon, Databento, Alpaca, Tardis.dev all REST). GraphQL's flexibility is a liability for a data product — unpredictable query costs, harder to rate-limit, harder for AI agents to use (agents work better with fixed endpoints). | REST only. Well-designed REST endpoints with query parameters for filtering. If users need flexible queries, the flat file downloads serve that use case. |
| **Mobile app** | Visual orderbook display, push notifications for market events. | Completely different product and skill set. Web dashboard is sufficient for API key management. The actual product is the API, not a UI. Mobile adds App Store review cycles, native development, push notification infrastructure. | Web-only dashboard for account management. The API is the product. PROJECT.md already excludes mobile. |
| **Redundant multi-connection data collection** | Multiple simultaneous websocket connections to Kalshi for data completeness and failover. | Correct long-term architecture, but premature for MVP. Kalshi's 1,000 market subscription limit per connection means one connection covers liquid markets. Adding redundancy before validating product-market fit is over-engineering. | Single websocket connection for MVP (covers liquid/popular markets). Add connection pooling and redundancy in a dedicated future milestone. PROJECT.md already scopes this out. |

## Feature Dependencies

```
[Data Collection (WS listener)]
    └──requires──> [Supabase Storage Schema]
                       └──required-by──> [Historical REST API]
                       └──required-by──> [Raw Delta Stream API]
                       └──required-by──> [Point-in-time Reconstruction]

[API Key Authentication]
    └──required-by──> [Rate Limiting]
    └──required-by──> [Usage Tracking]
    └──required-by──> [Tiered Pricing]
    └──required-by──> [Real-time WS Streaming]

[Rate Limiting]
    └──requires──> [API Key Authentication]
    └──required-by──> [Tiered Pricing]

[Tiered Pricing]
    └──requires──> [API Key Authentication]
    └──requires──> [Rate Limiting]
    └──requires──> [Usage Tracking]
    └──requires──> [Stripe Integration]

[Point-in-time Reconstruction]
    └──requires──> [Data Collection]
    └──requires──> [Ordered Delta Storage with Sequence Numbers]

[Real-time WS Streaming]
    └──requires──> [Data Collection]
    └──requires──> [API Key Authentication]

[Python SDK]
    └──requires──> [OpenAPI Spec]
    └──requires──> [Stable REST API]

[MCP Server]
    └──requires──> [Stable REST API]
    └──requires──> [OpenAPI Spec]

[Flat File Downloads]
    └──requires──> [Data Collection]
    └──requires──> [Tiered Pricing] (premium feature)

[Dashboard]
    └──requires──> [API Key Authentication]
    └──requires──> [Usage Tracking]
```

### Dependency Notes

- **Point-in-time Reconstruction requires Data Collection:** Cannot reconstruct without complete snapshot + delta history. Data completeness is existential.
- **Tiered Pricing requires Auth + Rate Limiting + Usage Tracking:** The entire billing stack must work together. Stripe integration ties it all together.
- **Python SDK requires Stable REST API:** Don't build SDK until API endpoints are stable. Auto-generate from OpenAPI to avoid drift.
- **MCP Server requires Stable REST API:** MCP tools wrap REST endpoints. Build after API is stable, not before.
- **Real-time WS Streaming requires Data Collection:** Re-broadcasts collected data. If collector is down, stream is down.
- **Flat File Downloads require Data Collection + Pricing:** Bulk data is expensive to serve. Must be gated behind premium tiers.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate demand for Kalshi orderbook data.

- [ ] **Data collection pipeline** — Websocket listener collecting L2 snapshots + deltas for liquid Kalshi markets. Without data, there is no product.
- [ ] **Historical orderbook REST API** — Query orderbook state at a given timestamp for a given market. Core use case: backtesting.
- [ ] **Point-in-time reconstruction engine** — Rebuild orderbook state from snapshot + deltas. This IS the core differentiator.
- [ ] **Raw delta stream endpoint** — Paginated access to raw deltas by market and time range. Advanced users want this.
- [ ] **Market metadata endpoint** — List available markets, contract details, data coverage dates.
- [ ] **API key authentication** — Issue keys, validate on requests, associate with usage.
- [ ] **Rate limiting** — Per-key rate limits with standard response headers.
- [ ] **Free tier** — 1,000 credits/month (or equivalent). Enables adoption without friction.
- [ ] **Basic API documentation** — OpenAPI spec auto-generated from FastAPI + hosted docs page.
- [ ] **Consistent JSON error responses** — Standard error envelope across all endpoints.

### Add After Validation (v1.x)

Features to add once core is working and there are paying users.

- [ ] **Pay-as-you-go + Project tiers** — Once free tier users convert, add paid tiers with Stripe.
- [ ] **Usage dashboard** — Show users their consumption, remaining credits, billing.
- [ ] **Real-time websocket streaming** — Add once historical API demand is validated. Higher complexity.
- [ ] **Python SDK** — Auto-generate from OpenAPI once endpoints are stable. Publish to PyPI.
- [ ] **`/llms.txt` discovery file** — Low effort, high signal for agent-first positioning.
- [ ] **Sequence number gap detection** — Add gap detection to delta streams for data integrity verification.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **MCP server** — Build after API is stable. Land-grab opportunity but needs solid foundation first.
- [ ] **Flat file downloads (CSV/Parquet)** — Bulk data access for large-scale backtesting. Premium feature.
- [ ] **Enterprise tier** — Custom rate limits, SLAs, dedicated support. Build when enterprise customers appear.
- [ ] **Connection pooling / full market coverage** — Scale beyond 1,000 market limit. Future milestone.
- [ ] **Derived metrics (spread, mid-price, order imbalance)** — Add 2-3 high-value computed fields after validating raw data demand.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Data collection pipeline | HIGH | HIGH | P1 |
| Historical orderbook REST API | HIGH | HIGH | P1 |
| Point-in-time reconstruction | HIGH | HIGH | P1 |
| Raw delta stream endpoint | HIGH | MEDIUM | P1 |
| Market metadata endpoint | MEDIUM | LOW | P1 |
| API key authentication | HIGH | MEDIUM | P1 |
| Rate limiting | HIGH | MEDIUM | P1 |
| Free tier (credit system) | HIGH | MEDIUM | P1 |
| OpenAPI documentation | HIGH | LOW | P1 |
| Consistent error responses | MEDIUM | LOW | P1 |
| Stripe billing (PAYG/Project) | HIGH | MEDIUM | P2 |
| Usage dashboard | MEDIUM | MEDIUM | P2 |
| Real-time WS streaming | HIGH | HIGH | P2 |
| Python SDK | MEDIUM | MEDIUM | P2 |
| `/llms.txt` discovery | MEDIUM | LOW | P2 |
| Agent-friendly response design | MEDIUM | LOW | P2 |
| MCP server | MEDIUM | MEDIUM | P3 |
| Flat file downloads | MEDIUM | MEDIUM | P3 |
| Enterprise tier | LOW (initially) | MEDIUM | P3 |
| Connection pooling | MEDIUM | HIGH | P3 |
| Derived metrics | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Polygon.io/Massive | Databento | Tardis.dev | Tavily | FinFeedAPI | KalshiBook Approach |
|---------|-------------------|-----------|------------|--------|------------|-------------------|
| **Data type** | Stocks, options, forex, crypto | Equities, futures, options (MBO/MBP/MBP-10 schemas) | Crypto orderbook, trades, funding, liquidations | Web search results | Prediction market prices, trades, OHLCV | Kalshi L2 orderbook snapshots + deltas |
| **Historical access** | REST API, flat files (S3) | REST API, batch download (binary/CSV/JSON), replay() | HTTP API (NDJSON), downloadable CSV | N/A | REST API | REST API for reconstruction + raw deltas |
| **Real-time** | WebSocket streaming | Streaming API (live) | Client library streaming (connects to exchanges) | N/A | N/A | WebSocket re-broadcast of collected data |
| **Orderbook depth** | L1 quotes, some L2 | Full depth: MBO (individual orders), MBP-10 (10 levels) | Full L2/L3 tick-level snapshots + incremental updates | N/A | Basic orderbook endpoint | Full L2 snapshots + deltas with reconstruction |
| **Point-in-time replay** | No (snapshots only) | Yes (replay() method, MBO snapshots every minute) | Yes (time-machine replay, core feature) | N/A | No | Yes (reconstruct to any timestamp) — core feature |
| **Pricing model** | Free (5 calls/min) through $200/mo advanced | $125 free credit, usage-based or flat $199/mo | Subscription plans, academic discounts, free trials | Free 1,000 credits, PAYG $0.008, Project $30, Enterprise | Unknown | Tavily-style credits: Free 1,000/mo, PAYG, Project, Enterprise |
| **Auth** | API key | API key (env var recommended) | API key (Bearer token) | API key | API key | API key |
| **SDKs** | Python, JS, Go, Java | Python, C++, Rust | Node.js, Python | Python, JS (community) | Unknown | Python (auto-generated from OpenAPI) |
| **Agent features** | MCP server available | Normalized schemas, DataFrame casting | Async iteration, composable replay | Built for agents: structured JSON, LLM-optimized responses, `/llms.txt` | Normalized cross-exchange data | Agent-first: `/llms.txt`, flat JSON, MCP server, Tavily-style design |
| **Data format** | JSON, CSV | DBN (binary), CSV, JSON, DataFrame/ndarray | NDJSON, CSV | JSON | JSON | JSON (REST), JSON (WS) |
| **Uptime** | 99.99% claimed | Not published | 99.9% data completeness | Sub-200ms average latency | Unknown | Target 99.9%+ |

## Sources

### Market Data APIs
- [Polygon.io/Massive](https://massive.com/) — Stock market data API, rebranded from Polygon.io. REST + WebSocket + flat files. SDKs in Python/JS/Go/Java. (MEDIUM confidence — fetched 2026-02-13)
- [Polygon.io Pricing](https://massive.com/pricing) — Free tier (5 calls/min), Starter $29/mo, Developer $79/mo, Advanced $200/mo. (MEDIUM confidence — pricing page was JS-rendered, data from search results)
- [Databento](https://databento.com/) — MBO/MBP schemas, $125 free credit, usage-based pricing, Python/C++/Rust clients. (MEDIUM confidence — fetched 2026-02-13)
- [Databento Schemas](https://databento.com/docs/schemas-and-data-formats) — MBO, MBP-1, MBP-10 schemas for orderbook data. (MEDIUM confidence — from search results)
- [Databento MBO Snapshots](https://databento.com/blog/live-MBO-snapshot) — Order book snapshots every minute for live data. (MEDIUM confidence — from search results)
- [Tardis.dev](https://tardis.dev/) — Crypto orderbook replay, 5,000+ TB historical data, 200,000+ instruments. (HIGH confidence — successfully fetched)
- [Tardis.dev HTTP API](https://docs.tardis.dev/api/http) — NDJSON format, minute-by-minute historical data, Bearer token auth. (HIGH confidence — successfully fetched)
- [Alpaca Market Data](https://docs.alpaca.markets/docs/about-market-data-api) — REST + WebSocket, trades/quotes/bars, crypto orderbook streaming. (MEDIUM confidence — from search results)

### Agent-Friendly APIs
- [Tavily](https://www.tavily.com/) — AI agent search API. Credit-based pricing, structured JSON responses. (HIGH confidence — pricing page fetched)
- [Tavily Pricing](https://www.tavily.com/pricing) — Free 1,000 credits, PAYG $0.008/credit, Project $30/mo, Enterprise custom. (HIGH confidence — successfully fetched)
- [Tavily API Credits](https://docs.tavily.com/documentation/api-credits) — Basic search: 1 credit, Advanced: 2 credits. (HIGH confidence — successfully fetched)
- [Exa AI](https://exa.ai/) — Semantic search API, $5/1,000 searches, enterprise tier. (MEDIUM confidence — from search results)
- [Exa Pricing](https://exa.ai/pricing) — Pay-per-use, $10 free credits, enterprise custom. (MEDIUM confidence — from search results)

### Prediction Market APIs
- [Kalshi Orderbook Responses](https://docs.kalshi.com/getting_started/orderbook_responses) — Bids-only model, [price, quantity] pairs, ascending order. (HIGH confidence — successfully fetched)
- [Kalshi WebSocket Orderbook](https://docs.kalshi.com/websockets/orderbook-updates) — Snapshot + delta model, requires auth. (HIGH confidence — partially fetched)
- [FinFeedAPI Prediction Markets](https://www.finfeedapi.com/products/prediction-markets-api) — Cross-exchange prediction market data aggregation. (LOW confidence — 403 blocked)
- [Polymarket API Architecture](https://medium.com/@gwrx2005/the-polymarket-api-architecture-endpoints-and-use-cases-f1d88fa6c1bf) — CLOB API, batch orders, WebSocket feeds. (MEDIUM confidence — from search results)

### Agent-Friendly API Design
- [How to make APIs ready for AI agents](https://www.digitalapi.ai/blogs/how-to-make-your-apis-ready-for-ai-agents) — OpenAPI 3.0+, self-describing endpoints, deterministic responses, MCP servers. (HIGH confidence — successfully fetched)
- [MCP Servers for Financial Data](https://medium.com/predict/top-5-mcp-servers-for-financial-data-in-2026-5bf45c2c559d) — Alpha Vantage, FMP, Polymarket MCP servers exist. (MEDIUM confidence — from search results)
- [Polygon.io MCP Server](https://www.pulsemcp.com/servers/polygon) — Official Polygon MCP server available. (MEDIUM confidence — from search results)

### API Monetization
- [API Rate Limiting Best Practices](https://developers.cloudflare.com/waf/rate-limiting-rules/best-practices/) — Per-key limits, response headers, multi-level limiting. (MEDIUM confidence — from search results)

---
*Feature research for: Monetized prediction market L2 orderbook data API*
*Researched: 2026-02-13*
