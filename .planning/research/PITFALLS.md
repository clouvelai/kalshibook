# Pitfalls Research: Python SDK + Backtesting Abstractions

**Domain:** Python SDK for monetized L2 orderbook data API (adding SDK to existing KalshiBook API)
**Researched:** 2026-02-17
**Confidence:** HIGH (verified against Azure SDK guidelines, PyPI official docs, real-world SDK post-mortems from DigitalOcean, community issue trackers, existing codebase analysis)

## Critical Pitfalls

### Pitfall 1: Unbounded Memory Growth in replay_orderbook()

**What goes wrong:**
The `replay_orderbook()` function fetches a snapshot then pages through all deltas in a time range, accumulating them in memory to reconstruct orderbook evolution. For active markets over long time periods, this can mean hundreds of thousands or millions of delta records. The naive implementation loads all pages into a list, applies them sequentially, and returns a full history. The SDK user's Python process runs out of memory and crashes -- or worse, triggers OS swap and degrades the entire machine.

**Why it happens:**
Developers build the replay function by concatenating all paginated responses into a single list before processing. It works perfectly during development with small test windows (5 minutes of data = a few hundred deltas). Then a user calls `replay_orderbook("KXBTC-25FEB17", start="2026-01-01", end="2026-02-01")` and requests a month of orderbook evolution for a high-volume market. The existing API returns up to 1000 deltas per page (see `DeltasRequest.limit` max), and a month of data could be 500K+ deltas. At roughly 200 bytes per delta record, that is 100MB+ in Python objects (dicts are 3-5x the raw data size due to object overhead).

**How to avoid:**
- Use an async generator (`async def replay_orderbook(...) -> AsyncIterator[OrderbookState]`) that yields one orderbook state per delta or per batch, never holding the full history in memory.
- Process deltas incrementally: fetch one page, apply to current book state, yield the state, then fetch the next page. Only hold one page of deltas + current book state at any time.
- Provide a `snapshot_interval` parameter that controls how often to yield -- e.g., yield a state every 100 deltas or every 60 seconds of market time, rather than on every individual delta.
- Add a `max_pages` safety parameter with a sensible default (e.g., 100 pages = 100K deltas). If exceeded, raise a clear error: "Time range too large. Use a narrower window or increase max_pages."
- Document the memory characteristics explicitly: "This function streams results. Use `async for state in replay_orderbook(...)` -- do not call `list()` on the result."

**Warning signs:**
- `replay_orderbook()` returns a `list` instead of an `AsyncIterator` / `AsyncGenerator`.
- No test with time ranges longer than 1 hour.
- No documentation warning about memory for large replays.
- Users reporting MemoryError or process kills when replaying long periods.

**Phase to address:**
Phase 1 (SDK Core Design) -- the replay abstraction's return type and streaming architecture must be designed correctly from the start. Retrofitting a list-based return into an async generator is a breaking change.

---

### Pitfall 2: Credit Burn Surprise -- Users Exhaust Credits Without Realizing It

**What goes wrong:**
`replay_orderbook()` internally makes many API calls (1 snapshot request = 5 credits, then N delta page requests = 2 credits each). A replay over a 24-hour period for an active market might require 200+ pages of deltas, costing 5 + (200 * 2) = 405 credits. A free-tier user has 1,000 credits/month. One call to `replay_orderbook()` burns 40% of their monthly allowance. Users call the function casually, hit `credits_exhausted` mid-replay, and lose both credits and the partial results.

**Why it happens:**
The SDK hides the pagination loop from the user -- that is the whole point. But hiding pagination also hides the cost. Users think "I'm making one function call" when the SDK is making 200+ API calls. The existing API returns `X-Credits-Remaining` and `X-Credits-Cost` headers (see `inject_credit_headers` middleware in `main.py`), but the SDK silently consumes these without surfacing them to the user.

**How to avoid:**
- Before starting the replay, call the `/deltas` endpoint once with `limit=1` to check if data exists and get the first cursor. Parse `X-Credits-Remaining` from the response header.
- Provide a `dry_run=True` option that estimates the number of pages needed (from the time range and typical delta density) and returns the estimated credit cost without actually fetching data.
- Surface credit information on every yielded state: include `credits_used_so_far` and `credits_remaining` fields in the response objects.
- Implement a `credit_budget` parameter: `replay_orderbook(ticker, start, end, credit_budget=100)`. If the replay would exceed this budget, stop and raise `CreditBudgetExceeded` with credits consumed so far.
- Raise `CreditsExhaustedError` with a clear message when the API returns 429 with `credits_exhausted`, rather than raising a generic HTTP error. Include how many credits were consumed before exhaustion.

**Warning signs:**
- No credit cost information in SDK response objects.
- Users discover credit exhaustion through raw HTTP 429 errors, not SDK-specific exceptions.
- No `credit_budget` or cost estimation mechanism.
- Support tickets from free-tier users saying "I made one call and all my credits are gone."

**Phase to address:**
Phase 1 (SDK Core Design) for the credit-aware interface design. Phase 2 (Replay Abstraction) for integrating credit tracking into the pagination loop.

---

### Pitfall 3: OpenAPI Auto-Generation Producing Unusable Python Code

**What goes wrong:**
The KalshiBook API uses FastAPI, which auto-generates an OpenAPI spec. You feed this spec into `openapi-generator` or `openapi-python-client` expecting a production-quality Python SDK. Instead you get: (a) generic exception handling that treats all non-2xx responses identically, losing the rich error codes (`credits_exhausted`, `market_not_found`, `rate_limit_exceeded`), (b) no async support (openapi-generator's Python output is sync-only by default), (c) verbose wrapper types that obscure the data (users have to navigate `response.data.data[0].market_ticker` instead of `response.markets[0].ticker`), (d) no pagination helpers, and (e) broken polymorphism when using `oneOf`/`anyOf` in the OpenAPI spec.

**Why it happens:**
OpenAPI generators are designed for breadth (50+ languages) not depth. DigitalOcean's post-mortem documented that `allOf`/`anyOf`/`oneOf` keywords caused openapi-generator to produce `UNKNOWNBASETYPE`, making endpoints unusable. The Python generator specifically lacks support for async/await, retry mechanisms, null/union types, and OAuth security schemes. The KalshiBook API has specific patterns (cursor-based pagination, credit headers, structured error envelopes) that no generator understands.

**How to avoid:**
- Do NOT auto-generate the SDK. Write it by hand. The KalshiBook API has only ~10 data endpoints -- this is a weekend of work, not a month. Hand-written code can be idiomatic, type-safe, and include the credit/pagination abstractions that are the SDK's entire value proposition.
- Use the OpenAPI spec for documentation and validation only, not code generation.
- If you must use a generator for initial scaffolding, use `openapi-python-client` (not `openapi-generator`) because it produces modern Python with type annotations and httpx. But plan to immediately rewrite the generated code.
- Model your SDK structure after the Azure SDK design guidelines: separate sync/async clients, ItemPaged protocol for collections, typed exceptions for each error code, credential parameter in constructor.

**Warning signs:**
- SDK contains generated code comments like `# TODO update the JSON string below`.
- Exception handling is a single `ApiException` class for all errors.
- Users have to import deeply nested generated module paths.
- Generated code does not use `async`/`await`.
- You are spending more time fighting the generator's output than writing code.

**Phase to address:**
Phase 1 (SDK Core Design) -- this is a "make or buy" decision that must be resolved before any SDK code is written. Choosing wrong means rewriting from scratch.

---

### Pitfall 4: Cursor Handling Bugs Creating Infinite Loops or Missing Data

**What goes wrong:**
The SDK's pagination loop has a subtle bug in cursor handling. The KalshiBook API uses a composite (timestamp, id) cursor encoded as base64 JSON (see `_encode_cursor` / `_decode_cursor` in `deltas.py`). Three failure modes: (1) The SDK receives `has_more=True` but `next_cursor=None` (should never happen, but the API has a code path where `rows` is empty despite `has_more`), and the SDK loops forever with no cursor. (2) The cursor is malformed (truncated base64, timezone-naive timestamp) and the API returns 422, which the SDK retries infinitely. (3) Time range boundary issues -- deltas at exactly `end_time` may or may not be included depending on `<=` vs `<` comparison (the API uses `<=` for deltas but `<` for trades), and the SDK does not normalize this, causing users to see different behavior for different endpoints.

**Why it happens:**
Cursor-based pagination looks simple but has many edge cases. The KalshiBook API's cursor encoding uses `datetime.fromisoformat()` which has different behavior for timezone-aware vs timezone-naive strings. The `_decode_cursor` function in `deltas.py` adds UTC if missing, but if the SDK generates a cursor locally (e.g., for seek-to-timestamp), it might produce a timezone-naive string. The `has_more` / `next_cursor` contract is also fragile: the API determines `has_more` by fetching `limit + 1` rows, but if exactly `limit + 1` rows exist, it returns `has_more=True` and a cursor pointing to a position with 0 remaining rows. The next request returns an empty `data` array with `has_more=False`, which is correct but unexpected.

**How to avoid:**
- Add defensive checks in the pagination loop: if `has_more=True` but `next_cursor is None`, break and log a warning. If `data` is empty regardless of `has_more`, break.
- Set a hard maximum iteration count (e.g., 10,000 pages). If reached, raise `PaginationError("Exceeded maximum page count -- possible infinite loop")`.
- Never construct cursors on the client side. Always use server-provided cursors only.
- Normalize time range semantics in the SDK: document and enforce that `start_time` is inclusive and `end_time` is exclusive for ALL endpoints, adding the appropriate adjustment for endpoints that use `<=` (like deltas).
- Write integration tests that paginate through a known dataset and verify total record count matches expectations. Test the edge case where total records are an exact multiple of page size.

**Warning signs:**
- SDK hangs indefinitely when replaying data.
- Users report "the last page is always empty" (this is actually correct behavior but feels like a bug).
- Inconsistent record counts when fetching the same data with different page sizes.
- No maximum iteration guard in the pagination loop.

**Phase to address:**
Phase 2 (Pagination Abstraction) -- must be designed with edge cases in mind. Integration tests against the real API are essential before release.

---

### Pitfall 5: PyPI Packaging Mistakes That Block Installation or Break User Environments

**What goes wrong:**
Five specific packaging failures: (1) Over-pinning dependencies -- requiring `pydantic>=2.12.5` (same version as the server) when the SDK only uses basic Pydantic v2 features. A user with `pydantic==2.8.0` in their project gets a dependency conflict and cannot install the SDK. (2) Missing `py.typed` marker file, so mypy/pyright users get no type checking benefits. (3) Publishing with `setup.py sdist bdist_wheel` instead of the modern `python -m build` + trusted publisher workflow, leaking PyPI API tokens. (4) Package name contains underscores (`kalshibook_sdk`) but the import uses hyphens or vice versa, causing import errors after `pip install`. (5) Shipping test files, dev dependencies, or the server code in the published package because `packages=find_packages()` includes everything.

**Why it happens:**
Python packaging has changed significantly and there are many legacy patterns in tutorials. The project already uses `pyproject.toml` (good), but the server's `pyproject.toml` bundles everything. The SDK needs its own `pyproject.toml` in a separate directory or a monorepo-aware build system. Pydantic version conflicts are the most common real-world SDK installation failure in 2025-2026 -- pydantic-core is tightly coupled to specific pydantic versions, and over-pinning cascades into every project that depends on both pydantic and the SDK.

**How to avoid:**
- Use minimal dependency bounds: `pydantic>=2.0,<3`, `httpx>=0.24`, not pinned to the exact version the server uses. Test against the minimum supported versions in CI.
- Create the SDK in a separate `sdk/` directory with its own `pyproject.toml`. Never ship server code in the SDK package.
- Include `py.typed` marker file for PEP 561 compliance.
- Use PyPI Trusted Publishing (OIDC) via GitHub Actions -- no API tokens to leak. Configure the publisher on pypi.org before first publish.
- Use `[project]` table in `pyproject.toml` (not `[tool.setuptools]`) with explicit `packages` listing. Verify the published package contents with `tar -tzf dist/*.tar.gz` before uploading.
- Ensure package name in `pyproject.toml` uses hyphens (`kalshibook-sdk`), import name uses underscores (`kalshibook_sdk`), and both are consistent.
- Test installation in a clean venv: `pip install dist/*.whl && python -c "from kalshibook_sdk import Client"`.

**Warning signs:**
- `pip install kalshibook-sdk` fails with `ResolutionImpossible` due to pydantic version conflict.
- `import kalshibook_sdk` raises `ModuleNotFoundError` after successful install.
- mypy reports `error: Skipping analyzing "kalshibook_sdk": module is installed, but missing library stubs or py.typed marker`.
- Published package contains `src/api/`, `tests/`, or `__pycache__/` directories.
- PyPI API token stored in GitHub secrets (should use trusted publishing instead).

**Phase to address:**
Phase 3 (Packaging & Publishing) -- but dependency bounds must be decided in Phase 1 when choosing which libraries the SDK uses. The `py.typed` marker and package structure should be set up at project scaffolding time.

---

### Pitfall 6: Auth Token Management Causing Silent Request Failures

**What goes wrong:**
The SDK stores the API key and makes authenticated requests. Three failure modes: (1) The user passes a Supabase JWT (from `/auth/login`) instead of an API key (starts with `kb-`), and the SDK sends it to data endpoints, which expect `kb-` keys. The API returns 401 with `invalid_api_key` but the error message ("The provided API key is invalid or has been revoked") does not mention the JWT/API-key distinction. (2) The user constructs the client with an expired or revoked key, and every request fails with 401 but the SDK does not raise a clear "your key is invalid" error on construction. (3) When the SDK is used in a long-running process (backtesting loop), the API key works initially but is revoked mid-process. Each subsequent request fails individually rather than the SDK detecting the pattern and raising a persistent auth failure.

**Why it happens:**
The KalshiBook API has two auth mechanisms: Supabase JWTs for account management (`/auth/*`, `/keys/*`) and API keys for data endpoints (`/orderbook`, `/deltas`, etc.). This dual-auth design is sensible for the API but confusing for SDK users. The error response from `InvalidApiKeyError` does not distinguish between "wrong auth mechanism" and "invalid key." The SDK user just sees 401 and does not know which credential to use.

**How to avoid:**
- Validate the API key format on client construction: `if not api_key.startswith("kb-"): raise ValueError("API key must start with 'kb-'. Did you pass a JWT access token? Use POST /auth/login to get a JWT, then POST /keys to create an API key.")`.
- Make one lightweight request (e.g., `GET /health` or a no-op) on client initialization to verify the key works. Surface auth failures immediately, not on the first data request.
- Implement a "persistent auth failure" detector: if 3 consecutive requests return 401, raise `AuthenticationError("API key appears to be revoked or invalid. Generate a new key at [dashboard URL].")` instead of retrying each request individually.
- Clearly document in the SDK README: "This SDK uses API keys (kb-...), not access tokens. Create an API key in the dashboard or via the /keys endpoint."

**Warning signs:**
- Users opening issues saying "I'm passing my login token but getting 401."
- No validation of API key format at client construction time.
- Long-running SDK processes silently failing on every request after key revocation.
- SDK constructor accepts any string as `api_key` without basic format validation.

**Phase to address:**
Phase 1 (SDK Core Design) -- auth handling is part of the client constructor, which is the first thing designed.

---

### Pitfall 7: SDK Version Coupled to API Version, Breaking Users on Every API Deploy

**What goes wrong:**
The SDK version and the API version are the same (`0.1.0`), or the SDK pins to a specific API contract. When the API adds a new optional field to a response (non-breaking on the API side), the SDK's Pydantic models reject the unknown field and raise `ValidationError`. When the API deprecates a field, old SDK versions break. Users are forced to upgrade the SDK every time the API changes, even for additive changes. This is especially painful because Python SDK upgrades may conflict with other dependencies.

**Why it happens:**
Pydantic v2's default behavior is to raise errors for unknown fields (`model_config = ConfigDict(strict=True)`) or ignore them silently depending on configuration. If the SDK uses strict validation, any new API field breaks old SDK versions. If it uses permissive validation, removed fields silently become `None`, causing `AttributeError` in user code that accessed them. Neither default is correct without explicit design.

**How to avoid:**
- SDK version is independent of API version. SDK `1.2.3` works with API `v1` -- any backward-compatible API change.
- Configure Pydantic models with `model_config = ConfigDict(extra="ignore")` -- unknown fields from newer API versions are silently dropped, not rejected. This is the forward-compatibility default.
- Never remove fields from SDK response models without a major version bump. Deprecate with warnings first.
- Use the API's `version` field (if/when added) or OpenAPI spec version for compatibility checks, not the SDK version.
- Include the SDK version in the `User-Agent` header (`KalshiBook-Python/1.2.3`) so the API can track SDK version distribution and know when it is safe to remove deprecated fields.
- Pin to an API version prefix in the base URL (e.g., `/v1/`) so the SDK is not affected by v2 deployments.

**Warning signs:**
- Users pinning the SDK to an exact version (`kalshibook-sdk==0.1.0`) because newer versions break.
- Pydantic `ValidationError` for unknown fields in SDK responses after an API deploy.
- SDK releases required for every API deploy, even non-breaking ones.
- No `User-Agent` header identifying the SDK version.

**Phase to address:**
Phase 1 (SDK Core Design) for model configuration and versioning strategy. Phase 3 (Packaging) for independent version numbering. The API should add `/v1/` prefix before the SDK ships.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Auto-generating SDK from OpenAPI spec | Fast initial client with all endpoints covered | Generic exceptions, no pagination helpers, no credit awareness, no async support. Must rewrite anyway for the replay abstraction | Never for this project -- the replay abstraction IS the SDK's value, and generators cannot produce it |
| Sync-only SDK (no async) | Simpler implementation, fewer tests | Users in async frameworks (FastAPI, asyncio-based bots) must wrap every call in `asyncio.run()`. Financial quant code increasingly uses asyncio | Only for initial alpha; async must come in v1.0 |
| Returning raw dicts instead of typed models | Faster development, no Pydantic dependency | No autocomplete, no type checking, runtime KeyErrors for typos, no forward-compatibility control | Never -- typed models are table stakes for a data SDK |
| Single HTTP client per function call (no session reuse) | Simpler per-function logic | Connection overhead on every call. replay_orderbook making 200+ requests without connection reuse is catastrophically slow | Never -- httpx.AsyncClient must be shared |
| Vendoring httpx or pydantic | Avoids dependency conflicts | Massive package size, security patches not inherited, confusing for users | Never |
| Publishing to PyPI with API token instead of trusted publisher | Works without OIDC setup | Token can leak, no attestation, manual rotation needed | Only for initial test publish to TestPyPI |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| KalshiBook API Auth | Accepting any string as API key in SDK constructor | Validate `kb-` prefix immediately. Provide clear error distinguishing API keys from JWTs |
| Credit Headers | Ignoring `X-Credits-Remaining` and `X-Credits-Cost` response headers | Parse and surface on every response object. Use for credit budget enforcement in replay functions |
| Cursor Pagination | Constructing cursors on the client side or caching cursors across sessions | Always use server-provided cursors from `next_cursor`. Cursors are opaque tokens -- do not decode or construct them |
| Error Responses | Treating all non-2xx as generic errors | Map `error.code` to specific exceptions: `CreditsExhaustedError`, `MarketNotFoundError`, `RateLimitError`, `ValidationError`, `AuthenticationError` |
| Rate Limit Headers | Ignoring `Retry-After` header on 429 responses | Parse `Retry-After` and implement automatic backoff. SDK should sleep and retry transparently (with configurable max retries) |
| Time Zones | Passing naive datetimes to API endpoints | SDK should reject timezone-naive datetimes or explicitly attach UTC. The API uses timezone-aware ISO 8601 timestamps |
| Deltas vs Trades boundary semantics | Assuming all endpoints use the same time range inclusion (`<=` vs `<`) | Deltas endpoint uses `ts <= end_time`, trades uses `ts < end_time`. SDK should normalize to consistent semantics (exclusive end) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Creating new httpx.AsyncClient per request | Connection establishment overhead, no HTTP/2 multiplexing, DNS resolution per call | Create client once in `__aenter__`, reuse for all requests, close in `__aexit__` | Noticeable at >10 requests. Catastrophic for replay (200+ requests) |
| Loading all paginated results into memory before yielding | MemoryError for large time ranges, long time-to-first-result | Use async generators that yield per-page results. Never call `list()` internally | >50 pages (50K deltas, ~10MB+ in Python objects) |
| No connection pooling limits | SDK opens unlimited connections to API, triggering server rate limits or connection exhaustion | Set `httpx.AsyncClient(limits=httpx.Limits(max_connections=10))` | >10 concurrent replay operations |
| Serializing/deserializing every response field | CPU overhead from full Pydantic validation on large delta arrays | Use `model_validate` with `strict=False`, consider `model_construct` for trusted API responses if performance-critical | >10K records per page (unlikely given current 1000 max limit, but relevant for future bulk endpoints) |
| Blocking event loop with CPU-bound orderbook reconstruction | UI/bot freezes during replay processing | Run delta application logic in executor if reconstruction is CPU-bound. For most cases, it is fast enough in-loop | >100K deltas applied to a single book state |
| No response caching for repeated identical requests | Redundant API calls and credit waste during development/testing | Provide optional `cache=True` parameter that caches GET requests by URL+params. Use TTL-based in-memory cache (not disk) | Development and testing. Production should not cache by default |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API key logged in debug output or exception tracebacks | Key leaked in log files, CI output, or error reporting services | Mask API key in all logging: show only prefix `kb-abc...`. Override `__repr__` on client class to mask key. Use httpx's `auth` parameter (masks in logs) rather than manually setting Authorization header |
| API key stored in source code or notebook cells | Key committed to version control, shared in notebooks | SDK docs must show `api_key=os.environ["KALSHIBOOK_API_KEY"]` pattern. Accept env var name as alternative to raw key: `Client.from_env("KALSHIBOOK_API_KEY")` |
| No TLS certificate verification | Man-in-the-middle attack intercepts API key and financial data | httpx verifies TLS by default. Never set `verify=False`. Document that self-signed certs are not supported |
| SDK sends credentials to wrong host | Phishing or DNS hijack steals API key | Hardcode the API base URL. Do not allow user-provided base URLs in production mode. If allowing custom base URL (for testing), validate HTTPS and warn on non-production domains |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Replay function returns raw delta records instead of structured orderbook states | User must implement their own snapshot+delta application logic -- defeating the purpose of the SDK | `replay_orderbook()` should yield `OrderbookState` objects with `yes_levels`, `no_levels`, `timestamp`, `spread`, and helper methods |
| No progress indication during long replays | User thinks the process is hung during a 200-page replay | Accept an optional `progress_callback` or log progress. Yield partial results so `async for` shows activity |
| Error messages reference HTTP status codes, not user actions | "HTTP 429" means nothing to a Python developer who has never seen the API docs | "Monthly credit limit reached. You have used 1000/1000 credits. Enable PAYG or upgrade at https://kalshibook.com/billing" |
| Inconsistent method naming between sync and async | `client.get_orderbook()` vs `async_client.async_get_orderbook()` -- cognitive overhead | Azure pattern: identical method names, different client classes. `Client.get_orderbook()` (sync) and `AsyncClient.get_orderbook()` (async) |
| No Jupyter notebook support | Financial data users overwhelmingly work in notebooks. `asyncio.run()` conflicts with notebook's event loop | Provide sync client that works in notebooks without async. Detect notebook environment and use `nest_asyncio` or provide `await`-ready methods |
| SDK requires reading API docs to understand credit costs | User has no idea that `replay_orderbook()` costs 5 + 2*N credits until they run out | Docstrings must state credit costs. `replay_orderbook()` should document "This function costs 5 credits for the initial snapshot plus 2 credits per page of deltas fetched." |

## "Looks Done But Isn't" Checklist

- [ ] **Replay abstraction:** Often missing empty-result handling -- verify that replaying a time range with no deltas returns an initial snapshot state, not an empty iterator
- [ ] **Replay abstraction:** Often missing mid-replay credit exhaustion -- verify that a `CreditsExhaustedError` raised on page 150 of 200 still provides the partial results collected so far (or at minimum, the count of credits consumed)
- [ ] **Pagination loop:** Often missing the "exact multiple" edge case -- verify that when total results = N * page_size, the final page does not trigger an unnecessary extra empty request
- [ ] **Error mapping:** Often missing mapping for all API error codes -- verify that `credits_exhausted`, `market_not_found`, `no_data_available`, `rate_limit_exceeded`, `invalid_api_key`, and `validation_error` each map to a distinct SDK exception class
- [ ] **PyPI package:** Often missing `py.typed` marker -- verify with `mypy --strict` that the installed package provides type information
- [ ] **PyPI package:** Often ships server code -- verify with `tar -tzf dist/*.tar.gz` that only `kalshibook_sdk/` files are included, not `src/api/` or `src/collector/`
- [ ] **Async client cleanup:** Often missing proper `__aexit__` -- verify that `async with Client(...) as client:` closes the httpx session. Test that using the client without context manager and not calling `close()` raises a ResourceWarning
- [ ] **Rate limit retry:** Often missing `Retry-After` header parsing -- verify that a 429 response with `Retry-After: 5` causes the SDK to sleep 5 seconds and retry, not use exponential backoff from 1 second
- [ ] **Timezone handling:** Often missing naive datetime rejection -- verify that `client.get_deltas(start_time=datetime(2026, 1, 1))` (no tzinfo) raises `ValueError`, not a silent UTC assumption
- [ ] **User-Agent header:** Often missing or generic -- verify that requests include `User-Agent: KalshiBook-Python/X.Y.Z` for API-side analytics and SDK version tracking
- [ ] **Sync client in notebooks:** Often broken because notebook already has an event loop -- verify that `Client` (sync) works in Jupyter without `nest_asyncio` or `asyncio.run()` hacks

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Memory explosion in replay (list-based return) | HIGH | Breaking change: `replay_orderbook()` return type changes from `list[OrderbookState]` to `AsyncIterator[OrderbookState]`. Requires major version bump (2.0.0). All user code using `results = replay_orderbook(...)` must change to `async for state in replay_orderbook(...)` |
| Credit burn surprise (users exhaust credits) | LOW | Add `credit_budget` parameter with backward-compatible default of `None` (unlimited). Add credit tracking to response objects. Non-breaking change, minor version bump |
| Auto-generated SDK in production | HIGH | Must rewrite from scratch. Generated code is fundamentally different in structure, naming, and error handling from a hand-written SDK. Users who depend on generated class names face a breaking migration |
| Cursor infinite loop | LOW | Fix the loop guard condition. Add `max_pages` parameter. Patch release. No breaking changes |
| Dependency conflict (pydantic over-pinned) | MEDIUM | Relax pydantic bound from `>=2.12.5` to `>=2.0,<3`. Test against minimum supported version. Patch release, but users who already gave up and uninstalled need to be re-acquired |
| Auth confusion (JWT vs API key) | LOW | Improve error messages and add format validation. Patch release. Update docs |
| API version coupling (SDK breaks on API change) | MEDIUM | Add `extra="ignore"` to all Pydantic models. Add `User-Agent` header. Minor version bump. Existing users must upgrade SDK to stop seeing ValidationErrors |
| Leaked API key in logs | MEDIUM | Add key masking. Patch release. Cannot un-leak already-logged keys. Users must rotate compromised keys |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Unbounded memory in replay | Phase 1: SDK Core Design | Profile memory during replay of 100K+ deltas. Verify peak memory stays under 50MB regardless of time range. Use `tracemalloc` in tests |
| Credit burn surprise | Phase 1: SDK Core Design + Phase 2: Replay | Write test that replays with `credit_budget=10` and verifies clean stop at budget. Check response objects include `credits_used` field |
| Auto-generation producing bad code | Phase 1: SDK Core Design | Decision point: hand-write vs generate. Verify by checking if `replay_orderbook()` exists (generators cannot produce it) |
| Cursor handling bugs | Phase 2: Pagination | Integration test with exact-multiple page sizes. Test with empty results. Test with invalid cursor. Verify max_pages guard triggers |
| PyPI packaging mistakes | Phase 3: Packaging | Install from TestPyPI into clean venv. Run `mypy --strict` on consuming code. Verify no server code in package. Test with `pydantic==2.0.0` minimum |
| Auth token management | Phase 1: SDK Core Design | Unit test: pass JWT → immediate ValueError. Unit test: pass revoked key → AuthenticationError on first call. Integration test: 3 consecutive 401s → persistent auth failure raised |
| SDK-API version coupling | Phase 1: SDK Core Design | Add unknown field to mock API response → verify SDK still parses correctly. Remove optional field → verify SDK gracefully handles `None` |
| Dependency conflicts | Phase 3: Packaging | CI matrix testing against pydantic 2.0, 2.5, 2.8, latest. CI matrix against httpx 0.24, 0.27, latest. Verify installation alongside common data science packages (pandas, numpy, polars) |
| Memory leak from unclosed httpx clients | Phase 1: SDK Core Design | Test client used without context manager → ResourceWarning. Test `async with` → clean close. Test client reuse across 1000 requests → no file descriptor leak |
| No Jupyter support | Phase 2: Sync Client | Test in actual Jupyter notebook. Verify sync client works without async event loop hacks |

## Sources

- [Azure Python SDK Design Guidelines](https://azure.github.io/azure-sdk/python_design.html) -- ItemPaged protocol, sync/async client patterns, error handling philosophy (HIGH confidence)
- [DigitalOcean Python SDK Generation Post-Mortem](https://www.digitalocean.com/blog/journey-to-python-client-generation) -- OpenAPI generator UNKNOWNBASETYPE failures, polymorphism issues (HIGH confidence)
- [Speakeasy OSS Python SDK Generator Comparison](https://www.speakeasy.com/docs/sdks/languages/python/oss-comparison-python) -- Feature gaps in openapi-generator: no async, no pagination, no retry (HIGH confidence)
- [OpenAPI Generator Issue #20826](https://github.com/OpenAPITools/openapi-generator/issues/20826) -- Bug report: generator produces unusable Python clients (HIGH confidence)
- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/) -- OIDC-based publishing, no API tokens needed (HIGH confidence)
- [PyPI Trusted Publisher Pitfalls](https://dreamnetworking.nl/blog/2025/01/07/pypi-trusted-publisher-management-and-pitfalls/) -- Name mismatch, hyphen/underscore confusion (HIGH confidence)
- [Python Rate Limiting Library Analysis](https://gist.github.com/justinvanwinkle/d9f04950083c4554835c1a35f9d22dad) -- Most Python rate limiting libraries are broken under concurrency (HIGH confidence)
- [Pydantic Dependency Conflict Issues](https://github.com/pydantic/pydantic/discussions/10670) -- pydantic-core version coupling breaks downstream packages (HIGH confidence)
- [Backtrader Memory Management](https://www.backtrader.com/blog/2019-10-25-on-backtesting-performance-and-out-of-memory/on-backtesting-performance-and-out-of-memory/) -- exactbars pattern for fixed-memory backtesting (MEDIUM confidence)
- [REST API SDK Design Patterns Analysis](https://vineeth.io/posts/sdk-development) -- Singleton vs OOP patterns, essential SDK capabilities (MEDIUM confidence)
- [Python Packaging User Guide](https://packaging.python.org/) -- Modern pyproject.toml packaging, build system configuration (HIGH confidence)
- [PEP 387 Backwards Compatibility Policy](https://peps.python.org/pep-0387/) -- Deprecation process, 2-year minimum deprecation period (HIGH confidence)
- [Semantic Versioning 2.0.0](https://semver.org/) -- Major.Minor.Patch versioning rules (HIGH confidence)
- KalshiBook API source code analysis -- `src/api/routes/deltas.py`, `src/api/deps.py`, `src/api/services/billing.py`, `src/api/errors.py`, `src/api/models.py` (HIGH confidence, direct codebase inspection)

---
*Pitfalls research for: Python SDK + Backtesting Abstractions for KalshiBook API*
*Researched: 2026-02-17*
