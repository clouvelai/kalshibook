# Phase 2: REST API + Authentication - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticated REST endpoints that serve historical orderbook data — reconstructed state at any timestamp, raw deltas, and market metadata — with rate limiting, structured errors, and auto-generated documentation. The API must support building backtesting systems (querying orderbook state at arbitrary historical points).

</domain>

<decisions>
## Implementation Decisions

### Design philosophy
- Agent-first API design — Tavily (tavily.com) as the reference product
- Consistent with Kalshi API conventions where it makes sense (field names, market identifiers)
- Every endpoint must work well for programmatic/automated consumers (AI agents, trading bots)
- API must support backtesting workflows: query orderbook state at any historical timestamp for any market

### URL & versioning
- Tavily-style flat endpoints (e.g., `/orderbook`, `/deltas`, `/markets`) — no `/v1/` prefix
- POST for complex queries (time ranges, filters), GET for simple lookups
- If versioning becomes needed later, handle via headers or new endpoints — not URL prefixes

### Authentication
- Supabase for user management (signup, login, password reset)
- API keys generated per user, sent via header (Tavily uses `Authorization: Bearer tvly-KEY`)
- Keys prefixed with `kb-` for easy identification (like Tavily's `tvly-` prefix)
- Key management endpoints: create, list, revoke

### Rate limiting
- Generous defaults for now — billing isn't wired until Phase 3
- Include standard rate-limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset) so clients are ready when limits tighten
- 429 responses with clear retry-after when exceeded

### Claude's Discretion
- Exact field naming for orderbook responses (mirror Kalshi vs cleaner schema) — optimize for agent consumption and backtesting clarity
- Response pagination strategy for delta queries
- Orderbook reconstruction endpoint design (how timestamp is specified, depth levels)
- Market metadata endpoint scope
- Error response body structure (follow Tavily's patterns as guide)
- OpenAPI spec generation approach
- /llms.txt content and structure

</decisions>

<specifics>
## Specific Ideas

- "I like the Tavily API overall as an agent-first example" — flat action-based endpoints, Bearer token auth, JSON POST bodies, SDK-friendly
- API must enable backtesting: a user should be able to request "what did the orderbook for market X look like at timestamp T" and get a complete, accurate response
- Tavily provides `llms.txt` for AI agent discovery — KalshiBook should do the same

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-rest-api-authentication*
*Context gathered: 2026-02-14*
