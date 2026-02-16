# Phase 6: API Playground - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Interactive API playground within the dashboard where users can configure requests, see generated curl commands, execute them live, and view responses. Scoped to Shell/curl only (Python/JavaScript tabs present but disabled). Launches with a single endpoint: orderbook reconstruction. Reference model: Tavily API Playground (app.tavily.com/playground).

</domain>

<decisions>
## Implementation Decisions

### Starting endpoint
- Launch with GET /markets/{ticker}/orderbook (the hero endpoint)
- market_ticker is the required field shown prominently
- Optional params (at timestamp, depth) go in collapsible "Additional fields" section — matches Tavily pattern and scales as we add more endpoints later

### Language tabs
- Shell tab active and functional
- Python and JavaScript tabs visible but disabled (grayed out styling)
- Hover tooltip on disabled tabs: "Coming soon"
- No click behavior on disabled tabs beyond the tooltip

### Code panel
- Dark theme code block with syntax highlighting (match Tavily aesthetic)
- Copy button in top-right corner
- Curl command updates in real-time as form values change
- API key masked in generated curl: `X-API-Key: kb_live_****...****`
- Shell tab shows well-formatted multi-line curl with backslash continuations

### Request execution
- Live execute from browser — "Send Request" button fires the request through Next.js API proxy
- Request costs credits (same as direct API call)
- Full-width prominent "Send Request" button (like Tavily)

### Response panel
- Toggles with Code panel via Response | Code tabs in top-right
- Two sub-tabs: JSON (syntax-highlighted, copyable) and Preview
- Response metadata shown (status code, response time, credits deducted)

### API key selector
- Dropdown populated with user's API keys
- Auto-selects first/default key — zero friction to first request
- Key displayed masked in dropdown (like Tavily: prefix visible, rest masked)

### "Try an example"
- Hardcoded example with a representative market ticker and timestamp
- Pre-fills form fields when clicked
- Future milestone will add dynamic live market examples

### Page layout
- Split panel: left = form config, right = code/response (like Tavily)
- Sidebar placement: after Overview, before API Keys — second item, prominent position
- Mobile: form stacks on top, code/response below (vertical stack, scroll to see results)

### Claude's Discretion
- Preview sub-tab format for orderbook data (table, summary card, or hybrid)
- Response metadata presentation (inline header bar vs. separate section)
- Exact syntax highlighting theme and color choices
- Loading/spinner state during request execution
- Error state presentation (invalid params, auth failures, credit exhaustion)
- Empty state before first request is sent

</decisions>

<specifics>
## Specific Ideas

- "Just like Tavily the way they do it is perfect" — Tavily API Playground is the north star reference
- Collapsible additional fields chosen explicitly to scale for future endpoints without UX rework
- Python/JS tabs should look clean when disabled — not broken, just "not yet"
- Future milestone planned around a "live" market example for users to try with — keep example mechanism pluggable

</specifics>

<deferred>
## Deferred Ideas

- Python SDK tab — requires client library (future milestone)
- JavaScript SDK tab — requires client library (future milestone)
- Dynamic "live market" example selection — separate milestone for curated demo data
- Additional endpoints beyond orderbook — add incrementally after launch

</deferred>

---

*Phase: 06-api-playground*
*Context gathered: 2026-02-16*
