# Requirements: KalshiBook

**Defined:** 2026-02-17
**Core Value:** Reliable, complete orderbook history for every Kalshi market — reconstructable to any point in time

## v1.1 Requirements

Requirements for Python SDK milestone. Each maps to roadmap phases.

### SDK Core

- [ ] **SDKC-01**: User can install SDK via `pip install kalshibook`
- [ ] **SDKC-02**: User can initialize client with API key (`KalshiBook(api_key="...")`)
- [ ] **SDKC-03**: User can initialize client from environment variable (`KalshiBook.from_env()`)
- [ ] **SDKC-04**: Client supports both sync and async usage patterns
- [ ] **SDKC-05**: SDK raises typed exceptions matching API error codes (AuthenticationError, RateLimitError, CreditsExhaustedError, etc.)
- [ ] **SDKC-06**: All responses include credit usage metadata (credits_used, credits_remaining)

### Data Endpoints

- [ ] **DATA-01**: User can query reconstructed orderbook at any timestamp (`client.get_orderbook(ticker, timestamp)`)
- [ ] **DATA-02**: User can iterate raw deltas with auto-pagination (`for delta in client.list_deltas(ticker, start, end)`)
- [ ] **DATA-03**: User can iterate trades with auto-pagination (`for trade in client.list_trades(ticker, start, end)`)
- [ ] **DATA-04**: User can list available markets with coverage dates (`client.list_markets()`)
- [ ] **DATA-05**: User can get market details (`client.get_market(ticker)`)
- [ ] **DATA-06**: User can query candles (`client.get_candles(ticker, interval)`)
- [ ] **DATA-07**: User can query settlements (`client.list_settlements()`)
- [ ] **DATA-08**: User can query events and event hierarchy (`client.list_events()`, `client.get_event(ticker)`)

### DataFrame Support

- [ ] **DFRA-01**: All list/paginated responses support `.to_df()` conversion to pandas DataFrame
- [ ] **DFRA-02**: pandas is an optional dependency (`pip install kalshibook[pandas]`)

### Documentation

- [ ] **DOCS-01**: mkdocs-material docs site with Getting Started guide
- [ ] **DOCS-02**: Authentication guide covering API key setup and from_env()
- [ ] **DOCS-03**: API reference auto-generated from docstrings
- [ ] **DOCS-04**: Code examples for each endpoint

### Packaging

- [ ] **PACK-01**: SDK published to PyPI with py.typed marker
- [ ] **PACK-02**: SDK uses uv workspace in monorepo (sdk/ directory)
- [ ] **PACK-03**: Minimal dependencies (httpx only, pandas optional)

## Future Requirements

Deferred to v1.2 milestone. Tracked but not in current roadmap.

### Backtesting Abstractions

- **BKTS-05**: `replay_orderbook()` streaming async generator reconstructing orderbook state delta-by-delta
- **BKTS-06**: `stream_trades()` iterator over historical trades with time range
- **BKTS-07**: `credit_budget` parameter to limit credit consumption on large queries

### SDKs

- **SDK-02**: TypeScript SDK auto-generated from OpenAPI spec
- **SDK-03**: JavaScript SDK auto-generated from OpenAPI spec

### Advanced Features

- **STRM-01**: User can subscribe to real-time orderbook updates via websocket
- **STRM-02**: Streaming requires valid API key authentication on connect
- **ADV-01**: MCP server exposing KalshiBook endpoints as AI agent tools
- **ADV-02**: Downloadable flat files (CSV/Parquet) for bulk backtesting

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Auto-generated SDK from OpenAPI | Hand-written is better for 10 endpoints; abstractions can't be generated |
| Real-time WebSocket streaming | Deferred to v1.2+ after data collection validates the model |
| Trade execution / order placement | Read-only data product, not a brokerage |
| GraphQL API | REST-only, better for agents, simpler to rate-limit |
| Mobile app | Web dashboard + API only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SDKC-01 | — | Pending |
| SDKC-02 | — | Pending |
| SDKC-03 | — | Pending |
| SDKC-04 | — | Pending |
| SDKC-05 | — | Pending |
| SDKC-06 | — | Pending |
| DATA-01 | — | Pending |
| DATA-02 | — | Pending |
| DATA-03 | — | Pending |
| DATA-04 | — | Pending |
| DATA-05 | — | Pending |
| DATA-06 | — | Pending |
| DATA-07 | — | Pending |
| DATA-08 | — | Pending |
| DFRA-01 | — | Pending |
| DFRA-02 | — | Pending |
| DOCS-01 | — | Pending |
| DOCS-02 | — | Pending |
| DOCS-03 | — | Pending |
| DOCS-04 | — | Pending |
| PACK-01 | — | Pending |
| PACK-02 | — | Pending |
| PACK-03 | — | Pending |

**Coverage:**
- v1.1 requirements: 23 total
- Mapped to phases: 0
- Unmapped: 23 ⚠️

---
*Requirements defined: 2026-02-17*
*Last updated: 2026-02-17 after initial definition*
