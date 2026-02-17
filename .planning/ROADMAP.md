# Roadmap: KalshiBook

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-02-17)
- [ ] **v1.1 Python SDK** — Phases 8-12 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-7) — SHIPPED 2026-02-17</summary>

- [x] Phase 1: Data Collection Pipeline (1/1 plans) — completed 2026-02-13
- [x] Phase 2: REST API + Authentication (3/3 plans) — completed 2026-02-14
- [x] Phase 3: Billing + Monetization (2/2 plans) — completed 2026-02-14
- [x] Phase 4: Backtesting-Ready API (4/4 plans) — completed 2026-02-15
- [x] Phase 5: Dashboard (5/5 plans) — completed 2026-02-16
- [x] Phase 6: API Playground (3/3 plans) — completed 2026-02-16
- [x] Phase 7: v1 Cleanup & Polish (1/1 plan) — completed 2026-02-17

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

</details>

### v1.1 Python SDK

**Milestone Goal:** Give users a first-class Python client for KalshiBook -- install via pip, query any endpoint with typed responses, auto-paginate large result sets, convert to DataFrames for analysis.

- [x] **Phase 8: SDK Scaffolding** (1/1 plans) — completed 2026-02-17
- [ ] **Phase 9: Models, Exceptions, and HTTP Transport** - Typed response models, exception hierarchy, httpx transport with auth/retry/credits
- [ ] **Phase 10: Client Class and Data Endpoints** - KalshiBook client with sync/async, all non-paginated endpoint methods
- [ ] **Phase 11: Pagination and DataFrame Support** - Auto-paginating async generators for cursor endpoints, .to_df() conversion
- [ ] **Phase 12: Documentation and PyPI Publishing** - mkdocs-material docs site, API reference, Getting Started guide, publish to PyPI

## Phase Details

### Phase 8: SDK Scaffolding
**Goal**: Users can install the SDK package and import the module in their Python environment
**Depends on**: Nothing (first phase of v1.1; v1.0 API is already deployed)
**Requirements**: PACK-02, PACK-03, SDKC-01
**Success Criteria** (what must be TRUE):
  1. Running `pip install -e ./sdk` in the monorepo installs the `kalshibook` package with no errors
  2. `from kalshibook import KalshiBook` succeeds in a Python 3.10+ interpreter
  3. `uv sync` at the workspace root resolves the SDK alongside the existing API code
  4. The installed package includes only SDK code (no server code leaks into the distribution)
  5. `py.typed` marker is present so mypy recognizes the package as typed
**Plans:** 1 plan
Plans:
- [x] 08-01-PLAN.md — SDK package structure, uv workspace integration, and distribution verification

### Phase 9: Models, Exceptions, and HTTP Transport
**Goal**: The SDK has typed response models for every API shape, a structured exception hierarchy matching API error codes, and an HTTP layer that handles auth injection, retry, and credit tracking
**Depends on**: Phase 8
**Requirements**: SDKC-02, SDKC-03, SDKC-04, SDKC-05, SDKC-06
**Success Criteria** (what must be TRUE):
  1. User can construct `KalshiBook(api_key="kb-...")` and `KalshiBook.from_env()` without errors
  2. Passing an invalid key format (e.g., a JWT or missing `kb-` prefix) raises a clear error at construction time
  3. API errors map to specific exception types (AuthenticationError, RateLimitError, CreditsExhaustedError, MarketNotFoundError) that users can catch individually
  4. Every response object exposes credit usage metadata (credits_used, credits_remaining)
  5. The client works in both `sync=True` mode (for scripts/notebooks) and async mode (for event loop contexts)
**Plans:** 3 plans
Plans:
- [ ] 09-01-PLAN.md — Exception hierarchy and datetime parsing utility
- [ ] 09-02-PLAN.md — All response dataclass models with from_dict factories
- [ ] 09-03-PLAN.md — HTTP transport (dual-mode, retry, error mapping) and KalshiBook client constructor

### Phase 10: Client Class and Data Endpoints
**Goal**: Users can query every non-paginated KalshiBook endpoint through typed client methods and get back structured response objects
**Depends on**: Phase 9
**Requirements**: DATA-01, DATA-04, DATA-05, DATA-06, DATA-08
**Success Criteria** (what must be TRUE):
  1. User can retrieve a reconstructed orderbook at any timestamp via `client.get_orderbook(ticker, timestamp)` and receive a typed OrderbookResponse
  2. User can list available markets with coverage dates via `client.list_markets()` and see which tickers have data
  3. User can get market details, candles, and event hierarchy via `client.get_market()`, `client.get_candles()`, `client.list_events()`, `client.get_event()`
  4. All returned objects are typed dataclasses with attribute access (e.g., `market.ticker`, `candle.open`) -- not raw dicts
**Plans:** 2 plans
Plans:
- [ ] 10-01-PLAN.md — Endpoint methods (sync + async) and private helpers on KalshiBook client
- [ ] 10-02-PLAN.md — Comprehensive endpoint tests with pytest-httpx mocks

### Phase 11: Pagination and DataFrame Support
**Goal**: Users can iterate over large result sets (deltas, trades, settlements) without manual cursor management, and convert any list result to a pandas DataFrame
**Depends on**: Phase 10
**Requirements**: DATA-02, DATA-03, DATA-07, DFRA-01, DFRA-02
**Success Criteria** (what must be TRUE):
  1. User can write `for delta in client.list_deltas(ticker, start, end)` and iterate all matching deltas across pages transparently
  2. User can write `for trade in client.list_trades(ticker, start, end)` and iterate all matching trades across pages transparently
  3. User can query settlements via `client.list_settlements()` with auto-pagination
  4. User can call `.to_df()` on any paginated result to get a pandas DataFrame with correctly typed columns
  5. pandas is optional -- `pip install kalshibook` works without pandas; `pip install kalshibook[pandas]` enables `.to_df()`
**Plans**: TBD

### Phase 12: Documentation and PyPI Publishing
**Goal**: Users can discover, install, and learn the SDK from PyPI and a hosted documentation site
**Depends on**: Phase 11
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, PACK-01
**Success Criteria** (what must be TRUE):
  1. A mkdocs-material documentation site builds with Getting Started guide, Authentication guide, and code examples for every endpoint
  2. API reference documentation is auto-generated from docstrings and covers all public methods
  3. `pip install kalshibook` installs the published package from PyPI
  4. The published package passes `mypy --strict` type checking in consumer code (py.typed works end-to-end)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 8 -> 9 -> 10 -> 11 -> 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Collection Pipeline | v1.0 | 1/1 | Complete | 2026-02-13 |
| 2. REST API + Authentication | v1.0 | 3/3 | Complete | 2026-02-14 |
| 3. Billing + Monetization | v1.0 | 2/2 | Complete | 2026-02-14 |
| 4. Backtesting-Ready API | v1.0 | 4/4 | Complete | 2026-02-15 |
| 5. Dashboard | v1.0 | 5/5 | Complete | 2026-02-16 |
| 6. API Playground | v1.0 | 3/3 | Complete | 2026-02-16 |
| 7. v1 Cleanup & Polish | v1.0 | 1/1 | Complete | 2026-02-17 |
| 8. SDK Scaffolding | v1.1 | 1/1 | Complete | 2026-02-17 |
| 9. Models, Exceptions, and HTTP Transport | v1.1 | 0/3 | Planned | - |
| 10. Client Class and Data Endpoints | v1.1 | 0/2 | Planned | - |
| 11. Pagination and DataFrame Support | v1.1 | 0/? | Not started | - |
| 12. Documentation and PyPI Publishing | v1.1 | 0/? | Not started | - |
