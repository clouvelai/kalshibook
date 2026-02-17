# Project Research Summary

**Project:** KalshiBook Python SDK + Backtesting Abstractions
**Domain:** Python SDK for monetized L2 prediction market orderbook data API
**Researched:** 2026-02-17
**Confidence:** HIGH

## Executive Summary

KalshiBook already has a deployed FastAPI backend with ~10 data endpoints (orderbook reconstruction, delta pagination, trades, candles, markets, events, settlements). This milestone wraps that API in a hand-written Python SDK — `pip install kalshibook` — targeted at quants and algo traders who want to backtest against Kalshi prediction market data. Research across four domains (stack, features, architecture, pitfalls) produces a coherent picture: hand-write the SDK using stdlib dataclasses and httpx; do not use a code generator; the high-level replay abstractions ARE the product and generators cannot produce them.

The recommended approach is a monorepo SDK at `sdk/` using uv workspaces, with a single `KalshiBook` client class, async-first design with sync wrapper, auto-paginating async generators for cursor-based endpoints, and a streaming `replay_orderbook()` abstraction that applies deltas client-side against an initial server-provided snapshot. Competitor analysis (Polygon, Databento, Alpaca, Tavily) validates the feature set: typed client, auto-pagination, structured exceptions, retry backoff, DataFrame conversion, and settlement data are all table stakes. The killer differentiator is `replay_orderbook()` — Databento-style historical event replay purpose-built for prediction market orderbooks.

The two most critical risks require Phase 1 design decisions: (1) `replay_orderbook()` must return an async generator, never a list — retrofitting this is a breaking change requiring a major version bump; (2) credit cost transparency must be built into the interface from the start, since the pagination loop hides the true API call count from users. A third structural risk — using a code generator — is strongly contraindicated by all four research files and must be rejected as a Phase 1 decision.

## Key Findings

### Recommended Stack

The existing backend stack (FastAPI, asyncpg, Supabase, Stripe) is unchanged. The SDK adds a clean new `sdk/` directory as a uv workspace member. Core SDK runtime dependencies are minimal: `httpx>=0.27` (HTTP transport, async and sync), stdlib `dataclasses` for models (no Pydantic in the SDK — lighter, faster, avoids version conflicts), and optionally `pandas>=2.0` behind `pip install kalshibook[pandas]`. Documentation uses `mkdocs-material ~9.7.1` + `mkdocstrings[python] ~2.0.2`. Development tooling adds `pytest-httpx ~0.35.x` for HTTP mocking, `mypy ~1.15.x` for type checking, and `ruff` for linting.

**Core technologies:**
- `httpx ~0.28.1`: HTTP transport (both sync and async in one library) — the only SDK runtime dep beyond stdlib
- `stdlib dataclasses` (slots=True, frozen=True): Response models — lighter than Pydantic, ~10x faster construction, no dependency conflicts with user projects
- `uv workspaces`: Monorepo with shared lockfile — keeps SDK and API in atomic sync; atomic changes when API model adds a field
- `uv publish` + PyPI Trusted Publishing: Credential-less CI publishing via OIDC — no tokens to leak
- `mkdocs-material ~9.7.1`: Documentation site — all Insiders features now free in 9.7.x; standard for modern Python SDKs (used by httpx, Pydantic)

**Rejected approaches:**
- `openapi-python-client` / `openapi-generator`: Cannot produce replay abstractions; generates generic exceptions losing rich error codes; generated output cannot handle the custom cursor-based pagination patterns or credit awareness that are the SDK's value; hand-writing 10 endpoints is a weekend of work not a month
- Pydantic in SDK models: Adds 2MB+ install size, creates pydantic-core version conflicts (most common SDK install failure in 2025-2026), unnecessary for read-only deserialization of already-validated server responses

Note: STACK.md explored `openapi-python-client` as a candidate; ARCHITECTURE.md and PITFALLS.md both reject code generation. The consensus across all four research files is hand-written SDK.

### Expected Features

**Must have (table stakes):**
- `KalshiBook(api_key=)` typed client with `KALSHIBOOK_API_KEY` env var fallback — every financial data SDK (Polygon, Databento, Alpaca, Tavily) initializes this way
- Context manager support (`async with KalshiBook() as client:`) — httpx connection pool cleanup, avoids ResourceWarning
- Structured exception hierarchy (`AuthenticationError`, `CreditsExhaustedError`, `MarketNotFoundError`, `RateLimitError`, `ValidationError`, `NoDataError`) — Tavily's typed exceptions are the best-in-class benchmark; Polygon's opaque 429 handling is a known user pain point
- Retry with exponential backoff on 429/5xx respecting `Retry-After` header — Tavily notably does NOT retry and users complain; make this the differentiator
- Auto-paginating async iterators for `/deltas` and `/trades` — Polygon's defining pattern: `async for delta in client.list_deltas(...):`
- Typed response models (stdlib dataclasses with `.from_dict()`) — users expect `trade.yes_price`, not `trade["yes_price"]`; type hints enable IDE autocomplete
- `.to_df()` on list results (optional pandas dep) — Databento and Alpaca both provide this; Polygon's lack of it is notable
- All endpoint wrappers: `get_orderbook()`, `list_deltas()`, `list_trades()`, `get_candles()`, `list_markets()`, `get_market()`, `list_events()`, `get_event()`, `list_settlements()`, `get_settlement()`
- Published to PyPI as `kalshibook`

**Should have (differentiators):**
- `replay_orderbook(ticker, start, end)` — async generator yielding `(timestamp, Orderbook)` tuples, applying deltas client-side to initial server snapshot; Databento's `replay()` applied to prediction market orderbooks; no other Kalshi data provider offers this
- `stream_trades(ticker, start, end)` — paginated trade history with replay semantics (thin alias over `list_trades()`)
- Credit tracking on every response (`credits_remaining`, `credits_used` from `X-Credits-*` headers)
- `credit_budget` parameter on replay functions to prevent runaway credit consumption
- `AsyncKalshiBook()` explicit async client or `sync=True` flag for Jupyter notebook users
- Notebook-friendly `_repr_html_()` for Jupyter rendering of orderbook snapshots
- Market discovery helpers with data coverage dates so users know what data exists before replaying

**Defer (v2+):**
- `backtest()` orchestrator with `Strategy` protocol — depends on replay + settlements being stable
- Backtrader / vectorbt integration adapters — only if community requests
- CLI tool (`kalshibook fetch-candles TICKER`) — only if non-programmatic use emerges
- WebSocket real-time streaming — KalshiBook is a historical data product; direct users to Kalshi's native WS for live data

### Architecture Approach

The SDK is a pure client-side addition — no server changes required. It lives at `sdk/` as a uv workspace member with its own `pyproject.toml`. The architecture has three layers: (1) a thin HTTP transport layer (`_http.py`) wrapping httpx with auth injection, error mapping, and credit header parsing; (2) a low-level client layer (`client.py`) with 1:1 endpoint methods and a pagination generator (`_pagination.py`); (3) high-level backtesting abstractions (`replay.py`) composing multiple client calls with domain logic (delta application to mutable Orderbook state). The `replay.py` layer is explicitly separate from `client.py` to keep the client focused on endpoint mapping.

**Major components:**
1. `KalshiBook` client class (`client.py`) — single entry point, all methods, sync/async unified, context manager lifecycle; single class is appropriate for 10 endpoints (Polygon pattern)
2. HTTP transport (`_http.py`) — httpx wrapper with auth injection, error envelope parsing, credit header tracking, retry with `Retry-After` respect
3. Pagination iterator (`_pagination.py`) — async generator following `next_cursor`/`has_more` transparently, with defensive guards against infinite loops and a hard `max_pages` cap
4. Typed models (`models.py`) — stdlib dataclasses with `from_dict()` classmethods mirroring API response shapes; `frozen=True, slots=True` for immutable responses; mutable `Orderbook` class for replay state
5. Replay abstractions (`replay.py`) — `replay_orderbook()` async generator: fetch initial snapshot via `POST /orderbook`, then auto-paginate deltas applying each to in-memory `Orderbook.apply_delta()`, yielding shallow copies per delta

**Key patterns:**
- Single client class (not resource-based) — appropriate for 10 endpoints; simpler autocomplete than `client.orderbook.get()`
- Async-first with sync wrapper — `httpx.AsyncClient` by default, `httpx.Client` when `sync=True`; avoids `asyncio.run()` which fails inside existing event loops
- Async generators for pagination and replay — constant memory usage regardless of dataset size
- Mutable `Orderbook` domain object mirrors server's `src/api/services/reconstruction.py` logic exactly

### Critical Pitfalls

1. **Unbounded memory in `replay_orderbook()`** — returning a list instead of an async generator causes MemoryError on large time ranges (500K+ deltas for a month of active market data at ~200 bytes per delta Python object). Retrofitting a list return to async generator is a breaking change requiring a major version bump. Must be async generator from day one; hold only one page + current book state in memory at any time.

2. **Credit burn surprise** — `replay_orderbook()` hides that it makes 200+ API calls (5 credits for snapshot + 2 per delta page). A free-tier user with 1,000 credits/month can exhaust 40% in one function call. Add `credit_budget` parameter, surface `credits_remaining` on every yielded state, and document credit cost per operation in all docstrings.

3. **Code generation producing unusable SDK** — OpenAPI generators cannot produce `replay_orderbook()`, generate a single generic exception losing all rich error codes, and lack async support. DigitalOcean's post-mortem shows `allOf`/`anyOf` causes generators to emit `UNKNOWNBASETYPE`. This is a Phase 1 decision — wrong choice means rewriting from scratch.

4. **Cursor pagination infinite loops** — the API's `has_more=True` with `next_cursor=None` edge case and the "empty last page" when `total = N * page_size` cause infinite loops without defensive guards. Required: break on empty `data` regardless of `has_more`; hard `max_pages` cap (default 10,000); never construct cursors client-side.

5. **PyPI packaging mistakes** — over-pinning dependencies (pydantic version conflicts are the most common SDK install failure in 2025-2026), missing `py.typed` marker (mypy users get no type checking), shipping server code in published package, hyphen/underscore naming inconsistency. Verify with `tar -tzf dist/*.tar.gz` before publish; test in a clean venv.

6. **Auth token confusion** — users pass Supabase JWTs instead of `kb-` API keys. Validate `kb-` prefix on construction with a clear error message distinguishing JWT from API key.

7. **SDK-API version coupling** — strict unknown-field handling causes old SDK versions to break when API adds any new response field. Use `extra="ignore"` semantics in `from_dict()` (silently ignore unknown keys); include `User-Agent: KalshiBook-Python/X.Y.Z` header for API-side analytics.

## Implications for Roadmap

The ARCHITECTURE.md build order maps directly to roadmap phases. The dependency chain is strict: scaffolding → models/exceptions → HTTP transport + client → pagination → replay abstractions → polish/publish.

### Phase 1: SDK Scaffolding + Core Architecture Decisions

**Rationale:** Must make three irreversible structural decisions before writing any logic: (1) hand-write vs generate (reject generation), (2) async generator return type for replay (not list), (3) dependency bounds and package structure. These decisions affect all subsequent phases and cannot be changed without breaking users.

**Delivers:** `sdk/` directory as uv workspace member; `sdk/pyproject.toml` with minimal deps (`httpx>=0.27`, optional `pandas>=2.0`); `kalshibook/__init__.py` with version and public surface; `py.typed` marker for PEP 561 compliance; confirmed `uv sync` resolves workspace; `sdk/src/` layout with all module stubs; API key format validation strategy decided.

**Addresses:** Package structure, dependency bounds, version independence from API, `py.typed` marker

**Avoids:** Code generation trap (Pitfall 3), SDK-API version coupling (Pitfall 7 — `from_dict()` ignores unknown keys by design), dependency conflicts (Pitfall 5 — minimal bounds), memory explosion architecture (Pitfall 1 — async generator return type locked in)

**Research flag:** Standard patterns. uv workspace and pyproject.toml are well-documented. No additional research needed.

### Phase 2: Models, Exceptions, and HTTP Transport

**Rationale:** All subsequent components depend on typed models and structured error handling. The exception hierarchy must mirror server error codes before any HTTP calls can be tested.

**Delivers:** All response dataclasses (`OrderbookResponse`, `DeltaRecord`, `TradeRecord`, `CandleRecord`, `MarketSummary`, `MarketDetail`, `EventSummary`, `EventDetail`, `SettlementRecord`); mutable `Orderbook` domain class with `apply_delta()` and computed properties (`best_yes`, `best_no`, `spread`); full exception hierarchy (`AuthenticationError`, `CreditsExhaustedError`, `MarketNotFoundError`, `RateLimitError`, `ValidationError`, `NoDataError`); `_http.py` with auth injection (`Authorization: Bearer kb-...`), error envelope parsing, credit header tracking, retry with `Retry-After` respect; API key format validation on construction.

**Addresses:** Typed response models, structured error handling, retry backoff, credit tracking, auth validation

**Avoids:** Auth token confusion (Pitfall 6 — validate `kb-` prefix in constructor), API version coupling (Pitfall 7 — `from_dict()` ignores unknown keys), leaked API key in logs (mask `kb-` key in `__repr__` and logging)

**Research flag:** Standard patterns. Dataclasses + httpx are well-documented; error code mapping is mechanical from existing API source.

### Phase 3: Client Class + Non-Paginated Endpoints

**Rationale:** With models and HTTP transport in place, the client class and all simple (non-paginating) methods can be implemented. This delivers a working SDK for the majority of endpoints.

**Delivers:** `KalshiBook` class with `sync=True` flag, `__aenter__`/`__aexit__` context manager, `get_orderbook()`, `get_market()`, `get_candles()`, `get_event()`, `get_settlement()`, `list_markets()`, `list_events()`, `list_settlements()`; unit tests mocked with `pytest-httpx`; `client.credits_remaining` property updated after each request; `User-Agent: KalshiBook-Python/X.Y.Z` header.

**Addresses:** Table stakes client API, market discovery, candles, settlements, all single-response endpoints

**Avoids:** New httpx client per request anti-pattern (connection pool must be shared across all requests in context manager lifetime)

**Research flag:** Standard patterns. Polygon and Alpaca precedents are clear. No additional research needed.

### Phase 4: Pagination Abstraction + Paginated Endpoints

**Rationale:** Cursor-based pagination is isolated in `_pagination.py` and powers `list_deltas()` and `list_trades()`. Must be correct and defensively guarded before replay abstractions can be built on top.

**Delivers:** `_pagination.py` async generator with defensive guards (break on empty data regardless of `has_more`, hard `max_pages=10000` cap, never construct cursors client-side); `list_deltas(ticker, start_time, end_time, limit=100)` and `list_trades(ticker, start_time, end_time, limit=100)` as auto-paginating async iterators; `.to_df()` on list results (optional pandas dep); integration tests against real API including exact-multiple page size edge case.

**Addresses:** Auto-pagination, DataFrame conversion, `stream_trades()` (thin alias)

**Avoids:** Cursor infinite loops (Pitfall 4 — all defensive guards here), memory explosion in paginated endpoints (Pitfall 1 — generator approach)

**Research flag:** Needs attention during planning. Two specific issues require codebase confirmation before implementation: (a) the deltas vs trades time boundary semantic difference (`<=` vs `<` for `end_time`) documented in PITFALLS.md must be verified from `src/api/routes/deltas.py` and `src/api/routes/trades.py`; (b) integration tests must cover the `total = N * page_size` edge case that produces an unnecessary empty final request.

### Phase 5: Replay Abstractions

**Rationale:** Depends on Phase 4 pagination being stable. `replay_orderbook()` is the SDK's signature feature and the primary reason users install it over raw HTTP calls. Also the highest-complexity phase.

**Delivers:** `replay.py` with `replay_orderbook(ticker, start, end, snapshot_interval=1, credit_budget=None)` async generator yielding `(datetime, Orderbook)` tuples; `Orderbook.apply_delta()` correctly mirroring server reconstruction logic; `credit_budget` parameter raising `CreditBudgetExceeded` if replay would exceed it; empty-range handling (yield initial snapshot state even if no deltas exist in range); `stream_trades()` as a replay-semantics alias; examples directory with working scripts.

**Addresses:** Orderbook replay (killer differentiator), credit burn transparency (Pitfall 2), notebook-friendly design

**Avoids:** Memory explosion (yields one state at a time, holds one page + current state); credit surprise (`credit_budget` + docstring cost documentation for every operation)

**Research flag:** Needs attention during planning. The delta application sign semantics in `Orderbook.apply_delta()` must be verified against `src/api/services/reconstruction.py` before implementation. A wrong sign convention produces silently incorrect orderbook states — the most dangerous bug possible for a backtesting SDK because it looks correct. Also confirm the exact credit cost per endpoint (orderbook=5, deltas page=2, candles=3) from the billing service before documenting in docstrings.

### Phase 6: Polish, Documentation, and PyPI Publishing

**Rationale:** SDK is feature-complete; this phase makes it distributable and discoverable. Incorrect packaging cannot be fixed after first publish without a version bump.

**Delivers:** `mkdocs-material` documentation site with Getting Started, Authentication, Backtesting Quickstart, and API Reference (auto-generated via `mkdocstrings[python]`); docstrings on all public methods including credit cost per operation; `examples/` with quickstart, replay, and backtest strategy scripts; PyPI publish via `uv publish` + Trusted Publishing OIDC (no tokens); GitHub Actions workflow for publish-on-tag; verified `tar -tzf dist/*.tar.gz` contains only SDK code; install tested in clean venv; `mypy --strict` passes on consumer code.

**Addresses:** PyPI publishing, documentation, package verification

**Avoids:** PyPI packaging mistakes (Pitfall 5 — all verification steps explicit), API token leakage (use Trusted Publishing OIDC, not API tokens)

**Research flag:** Standard patterns. uv publish + PyPI Trusted Publishing have clear official documentation. mkdocs-material setup is mechanical.

### Phase Ordering Rationale

- **Phases 1-3 are strictly sequential**: scaffolding → models → client. Each is a hard dependency of the next.
- **Phase 4 before Phase 5**: Pagination is the foundation of replay; `replay_orderbook()` cannot be built until `list_deltas()` is correct and defensively guarded.
- **Phase 6 last**: Publishing a broken or incomplete SDK damages trust and cannot be undone. Feature phases must complete first.
- **Credit awareness (Pitfall 2) spans Phases 1, 2, and 5**: Design decision in Phase 1 (interface includes credit tracking), implementation in Phase 2 (`_http.py` parses credit headers), integration in Phase 5 (`replay.py` uses credit budget). This cross-cutting concern must be tracked across phases.
- **The code generation question (Pitfall 3) must be resolved in Phase 1**: Any code generation approach changes the entire architecture. Resolving it in Phase 1 is the most consequential single decision in the roadmap.
- **No server changes required**: All phases are purely additive. The existing API, collector, and dashboard are untouched.

### Research Flags

Phases needing deeper research during planning:

- **Phase 4 (Pagination):** Before implementation, confirm from API source: does the deltas endpoint use `ts <= end_time` and trades use `ts < end_time`? This determines whether the SDK normalizes to a consistent exclusive-end convention or preserves endpoint-specific semantics.
- **Phase 5 (Replay):** Before implementation, verify `Orderbook.apply_delta()` sign semantics against `src/api/services/reconstruction.py` (specifically the delta_amount sign convention for quantity decreases vs increases) and confirm credit costs per endpoint from `src/api/services/billing.py`.

Phases with standard patterns (can skip research-phase):

- **Phase 1 (Scaffolding):** uv workspaces, pyproject.toml, py.typed are thoroughly documented.
- **Phase 2 (Models/HTTP):** stdlib dataclasses + httpx are mature; error mapping is mechanical from existing API error codes.
- **Phase 3 (Client):** Single client class with context manager is standard across Polygon, Alpaca, Tavily.
- **Phase 6 (Publishing):** uv publish + PyPI Trusted Publishing have clear official documentation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All sources are official docs or actively-maintained library pages. The uv + httpx + dataclasses choice is well-validated. One internal disagreement (STACK.md explored openapi-python-client; ARCHITECTURE.md and PITFALLS.md reject code generation) resolves clearly in favor of hand-writing — the consensus across 3 of 4 research files is decisive. |
| Features | HIGH | Competitor analysis against 4 production SDKs (Polygon, Databento, Alpaca, Tavily) with source code review. KalshiBook API endpoints reviewed directly. Feature dependency graph mapped. MVP vs v1.x vs v2+ scope is well-defined. |
| Architecture | HIGH | Verified against Azure SDK design guidelines, Polygon.io and Alpaca source code, existing KalshiBook API source code. The mutable `Orderbook.apply_delta()` pattern mirrors the server's own reconstruction service. The build order (6 steps) is driven by clear hard dependencies. |
| Pitfalls | HIGH | 7 critical pitfalls identified. Sources include: DigitalOcean post-mortem (code generation), Azure SDK guidelines (error hierarchy, sync/async), PyPI official docs (packaging), pydantic/pydantic-core issue trackers (dependency conflicts), direct KalshiBook codebase analysis (cursor encoding, error codes, credit headers). The cursor edge cases and credit burn scenarios are specific to this API's implementation. |

**Overall confidence:** HIGH

### Gaps to Address

- **Delta application sign semantics**: ARCHITECTURE.md documents `apply_delta()` as `book[price] = book.get(price, 0) + delta.delta_amount` and removes the level if `<= 0`. This must be verified against `src/api/services/reconstruction.py` during Phase 5 planning. A wrong sign convention produces silently incorrect orderbook states — the worst possible bug for a backtesting SDK.

- **`AsyncKalshiBook` vs `sync=True` flag**: ARCHITECTURE.md recommends a single class with `sync=True` flag; FEATURES.md mentions `AsyncKalshiBook()` as a separate class for v1.x. Trade-off: single class = simpler maintenance; separate classes = cleaner type signatures for users. Decide in Phase 1. Research leans toward single class with flag.

- **Endpoint time boundary semantics**: PITFALLS.md documents that deltas uses `ts <= end_time` while trades uses `ts < end_time`. This needs confirmation from API source code during Phase 4 planning before the SDK normalizes semantics.

- **Credit costs per endpoint**: ARCHITECTURE.md documents specific costs (orderbook=5, deltas page=2, trades page=2, markets=1, candles=3) but these should be confirmed against `src/api/services/billing.py` before publishing SDK docstrings.

- **Minimum Python version**: Research targets Python 3.10+ (`dataclasses` with `slots=True` requires 3.10). Confirm this is acceptable for the target user base — some quant environments still run Python 3.8/3.9.

## Sources

### Primary (HIGH confidence)
- [Polygon.io Python Client (GitHub)](https://github.com/polygon-io/client-python) — auto-pagination pattern, single client class architecture, retry configuration
- [Databento Python Client (GitHub)](https://github.com/databento/databento-python) — replay() pattern, DataFrame conversion, Historical client design
- [Alpaca-py (GitHub)](https://github.com/alpacahq/alpaca-py) — Pydantic models usage, financial data SDK patterns
- [Tavily Python Client (GitHub)](https://github.com/tavily-ai/tavily-python) — best-in-class typed exception hierarchy
- [Azure Python SDK Design Guidelines](https://azure.github.io/azure-sdk/python_design.html) — sync/async client patterns, error handling philosophy
- [DigitalOcean Python SDK Generation Post-Mortem](https://www.digitalocean.com/blog/journey-to-python-client-generation) — confirmed OpenAPI generator `UNKNOWNBASETYPE` failures
- [uv Workspaces documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/) — monorepo workspace configuration
- [uv build backend docs](https://docs.astral.sh/uv/concepts/build-backend/) — uv_build ~0.10.3, pure Python support
- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/) — OIDC publishing
- [mkdocs-material PyPI / Insiders announcement](https://squidfunk.github.io/mkdocs-material/) — v9.7.1 all features free
- [mkdocstrings (GitHub)](https://github.com/mkdocstrings/mkdocstrings) — API doc auto-generation from docstrings
- [httpx async docs](https://www.python-httpx.org/async/) — AsyncClient, streaming, connection pooling
- KalshiBook API source code (`src/api/`) — error codes, cursor encoding, credit headers, reconstruction logic (direct inspection)

### Secondary (MEDIUM confidence)
- [Speakeasy OSS Python SDK Generator Comparison](https://www.speakeasy.com/docs/sdks/languages/python/oss-comparison-python) — openapi-generator limitations: no async, no pagination (vendor source, potential bias)
- [Stainless: Build vs Buy SDKs](https://www.stainless.com/blog/build-vs-buy-sdks) — generation tradeoffs
- [openapi-python-client GitHub](https://github.com/openapi-generators/openapi-python-client) — explored as candidate; rejected for hand-written approach
- [Pydantic Dependency Conflict Issues](https://github.com/pydantic/pydantic/discussions/10670) — pydantic-core version coupling breaks downstream packages
- [Backtrader Memory Management](https://www.backtrader.com/blog/2019-10-25-on-backtesting-performance-and-out-of-memory/) — fixed-memory backtesting patterns

### Tertiary (LOW confidence)
- DataFrame column naming conventions from blog posts — specific conventions need validation against actual Databento/Alpaca output during implementation

---
*Research completed: 2026-02-17*
*Ready for roadmap: yes*
