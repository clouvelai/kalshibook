# Phase 8: SDK Scaffolding - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the `kalshibook` Python SDK as a uv workspace member in the monorepo. Users can `pip install -e ./sdk` and `from kalshibook import KalshiBook`. No client logic yet — just package infrastructure, empty module structure, and workspace integration.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
User trusts Claude to design the SDK foundation correctly. All scaffolding decisions are at Claude's discretion, guided by:

**Locked decisions from prior research:**
- Hand-written SDK (no code generation)
- httpx + stdlib dataclasses (no Pydantic — avoids version conflicts)
- Single `KalshiBook` class with `sync=True` flag (not separate AsyncKalshiBook)
- Replay abstractions deferred to v1.2

**Areas where Claude decides:**
- Module layout (flat vs nested subpackages, how to organize client/models/exceptions/transport)
- Top-level exports (what's importable from `kalshibook` directly)
- Package metadata (description, classifiers, license)
- Minimum Python version (success criteria says 3.10+)
- SDK directory location within the monorepo
- Development tooling (test runner, linting config for SDK)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow Python packaging best practices and conventions familiar to data/finance library users.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-sdk-scaffolding*
*Context gathered: 2026-02-17*
