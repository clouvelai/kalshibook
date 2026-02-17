# Phase 9: Models, Exceptions, and HTTP Transport - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Typed response models for every API shape, a structured exception hierarchy matching API error codes, and an HTTP transport layer (httpx) that handles auth injection, retry with backoff, and credit tracking. This is the foundation layer of the Python SDK — every client method in Phase 10 will build on these primitives.

</domain>

<decisions>
## Implementation Decisions

### Auth and client construction
- API key as first **positional** arg: `KalshiBook("kb-...")`
- Env var fallback: `KALSHIBOOK_API_KEY` — `KalshiBook()` reads from env automatically
- `base_url` param with production default — configurable for local/staging: `KalshiBook("kb-...", base_url="http://localhost:8000")`
- `sync=True` by default (scripts/notebooks are the primary audience). Async users opt in with `sync=False`
- Single `KalshiBook` class (not separate sync/async classes like Tavily)

### Response model shape
- Stdlib `dataclasses` (no Pydantic) — already decided
- Field names match API JSON exactly (no renaming)
- Timestamp fields parsed into `datetime` objects (not raw ISO strings) — consistent with typed philosophy
- Credit/request metadata nested under `.meta` (not top-level)
- `.meta` includes: `credits_used`, `credits_remaining`, `response_time`
- `client.usage()` method for standalone balance check (hits billing API)

### Claude's Discretion
- Nested vs flat dataclass structure (whether inner objects like orderbook levels get their own dataclass)
- Exact dataclass field ordering
- Whether `.meta` is its own dataclass or a simple NamedTuple

### Exception hierarchy
- All exceptions inherit from `KalshiBookError` base class — users can `except KalshiBookError` to catch everything
- Specific subclasses: `AuthenticationError`, `RateLimitError`, `CreditsExhaustedError`, `MarketNotFoundError`
- `CreditsExhaustedError` is distinct (not grouped under generic PaymentError) — users catch it specifically to handle "out of credits" differently
- Every API exception carries: `status_code`, `response_body`, and human-readable `message`
- 429 rate limits: SDK auto-retries with exponential backoff (3 attempts) transparently

### Credit tracking UX
- Credit metadata always included on every response (not opt-in like Tavily's `include_usage`)
- Accessed via `response.meta.credits_used`, `response.meta.credits_remaining`
- Silent — no automatic warnings at low balance. User checks `.meta` themselves
- `client.usage()` method available for explicit balance check without a data call

</decisions>

<specifics>
## Specific Ideas

- Tavily Python SDK used as design reference — adapted for KalshiBook's typed dataclass approach
- Tavily pattern: minimal client constructor, feature parity between sync/async — adopted
- Tavily pattern: plain dict responses — rejected in favor of typed dataclasses for IDE autocomplete and type safety
- Tavily pattern: separate sync/async client classes — rejected in favor of single class with `sync` flag (already decided)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-models-exceptions-and-http-transport*
*Context gathered: 2026-02-17*
