---
phase: 02-rest-api-authentication
plan: 03
subsystem: api
tags: [supabase-auth, httpx, jwt, api-keys, llms-txt, openapi, fastapi]

# Dependency graph
requires:
  - phase: 02-rest-api-authentication
    plan: 01
    provides: "FastAPI app, Pydantic models, API key auth service, stub routes, error handling"
provides:
  - "Auth proxy endpoints: POST /auth/signup, POST /auth/login via Supabase GoTrue REST API"
  - "Key management endpoints: POST /keys, GET /keys, DELETE /keys/{key_id} with JWT auth"
  - "SupabaseAuthClient using httpx directly (avoids supabase-py websockets conflict)"
  - "get_authenticated_user dependency for Supabase JWT validation"
  - "AI agent discovery: /llms.txt and /llms-full.txt (515-line comprehensive reference)"
  - "Enhanced OpenAPI metadata with tagged endpoint groups"
affects: [03-billing]

# Tech tracking
tech-stack:
  added: []
  patterns: [supabase-gotrue-httpx-client, jwt-vs-apikey-auth-separation, llms-txt-discovery]

key-files:
  created:
    - src/api/routes/auth.py
    - src/api/services/supabase_auth.py
    - static/llms.txt
    - static/llms-full.txt
  modified:
    - src/api/routes/keys.py
    - src/api/deps.py
    - src/api/main.py

key-decisions:
  - "Used httpx directly against Supabase GoTrue REST API instead of supabase-py (websockets<16 conflict unresolvable)"
  - "Separated JWT auth (key management) from API key auth (data endpoints) via distinct dependencies"
  - "llms-full.txt at 515 lines covers full auth flow, all endpoints, error codes, backtesting workflow"

patterns-established:
  - "SupabaseAuthClient: thin httpx wrapper around GoTrue /signup, /token, /user endpoints"
  - "get_authenticated_user: validates Supabase JWT, rejects kb- API keys with clear error message"
  - "llms.txt served via PlainTextResponse routes excluded from OpenAPI schema"

# Metrics
duration: 5min
completed: 2026-02-14
---

# Phase 2 Plan 3: Auth Proxy, Key Management, and AI Discovery Summary

**Supabase auth proxy (signup/login) via httpx GoTrue client, full key management CRUD with JWT auth, and llms.txt AI agent discovery files**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-14T15:38:27Z
- **Completed:** 2026-02-14T15:43:31Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Auth proxy endpoints working: POST /auth/signup and POST /auth/login proxy to Supabase GoTrue REST API
- Key management endpoints fully implemented: create (returns raw key once), list (prefixes only), revoke
- JWT auth dependency cleanly separates Supabase token auth from API key auth with informative error messages
- Comprehensive AI agent discovery: /llms.txt (concise) and /llms-full.txt (515-line full reference)
- OpenAPI spec enhanced with tag descriptions for all endpoint groups
- Resolved supabase-py websockets conflict by building a thin httpx GoTrue client

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement auth proxy and key management endpoints** - `8aa5abf` (feat)
2. **Task 2: Create llms.txt discovery files and configure OpenAPI metadata** - `a3e20f5` (feat)

## Files Created/Modified

- `src/api/routes/auth.py` - Auth proxy: POST /auth/signup and POST /auth/login
- `src/api/services/supabase_auth.py` - SupabaseAuthClient using httpx against GoTrue REST API
- `src/api/routes/keys.py` - Full key management: POST /keys, GET /keys, DELETE /keys/{key_id}
- `src/api/deps.py` - Added get_authenticated_user dependency for Supabase JWT validation
- `src/api/main.py` - Supabase client init in lifespan, auth router, llms.txt routes, OpenAPI tags
- `static/llms.txt` - AI agent discovery file (llms.txt spec)
- `static/llms-full.txt` - Comprehensive API reference for AI agents (515 lines)

## Decisions Made

- **httpx instead of supabase-py**: The supabase Python package requires websockets>=11,<16 through its `realtime` dependency, which is incompatible with websockets>=16.0 used by the Kalshi WebSocket collector. Built a thin SupabaseAuthClient using httpx to call the GoTrue REST API directly (/auth/v1/signup, /auth/v1/token, /auth/v1/user). This avoids the dependency conflict entirely and is simpler than the full supabase-py SDK.
- **JWT vs API key auth separation**: Key management endpoints use get_authenticated_user (Supabase JWT validation) while data endpoints use get_api_key (API key hash lookup). If a user sends a kb- API key to a JWT-only endpoint, they get a clear error explaining they need a Supabase access token.
- **llms-full.txt scope**: Made it comprehensive enough for an AI agent to integrate without reading any other docs -- includes full auth workflow, all request/response schemas, error codes, rate limiting details, and a backtesting example.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Built custom Supabase Auth client instead of using supabase-py**
- **Found during:** Task 1 (auth proxy implementation)
- **Issue:** supabase-py requires websockets>=11,<16 via its `realtime` dependency, incompatible with websockets>=16.0 (Kalshi collector). This was a known blocker from Plan 02-01.
- **Fix:** Created `src/api/services/supabase_auth.py` -- a thin async httpx wrapper around the Supabase GoTrue REST API. Covers signup, login, and JWT validation. No supabase-py needed.
- **Files modified:** src/api/services/supabase_auth.py (new), src/api/routes/auth.py, src/api/main.py
- **Verification:** `uv run python -c "from src.api.services.supabase_auth import SupabaseAuthClient; print('OK')"` succeeds
- **Committed in:** 8aa5abf (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The httpx GoTrue client is functionally equivalent to using supabase-py for auth operations. The API surface is the same (signup, login, get_user). No features lost. This permanently resolves the websockets version conflict blocker.

## Issues Encountered

None beyond the supabase-py conflict documented above as a deviation.

## User Setup Required

Supabase must be running with email auth enabled. Required environment variables:
- `SUPABASE_URL` - Supabase project URL (default: http://127.0.0.1:54321 for local dev)
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key from Supabase Dashboard -> Settings -> API

## Next Phase Readiness

- Phase 2 complete: all three plans (01-foundation, 02-data-endpoints, 03-auth-endpoints) delivered
- Full auth flow works: signup -> login -> create key -> use key on data endpoints
- All developer experience requirements satisfied: OpenAPI spec, Swagger UI, ReDoc, llms.txt
- Ready for Phase 3 (billing/subscriptions) which will wire rate limits to subscription tiers

## Self-Check: PASSED

- All 7 created/modified files verified on disk
- Both task commits verified in git log (8aa5abf, a3e20f5)

---
*Phase: 02-rest-api-authentication*
*Completed: 2026-02-14*
