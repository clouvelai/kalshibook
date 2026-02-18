Verify the KalshiBook dashboard works correctly in Chrome by walking through each page, taking screenshots, and validating key UI elements.

## Prerequisites

- Chrome extension connected (tabs_context_mcp returns tabs)
- Dashboard dev server running at localhost:3000
- Backend API running at localhost:8000

## Steps

### 1. Get Chrome Context

Call `tabs_context_mcp` to confirm the extension is connected. Create a new tab with `tabs_create_mcp`.

### 2. Authenticate

Run `bash scripts/dev-login.sh` to generate tokens. Parse the output for the dev-session URL (it contains `localhost:3000/auth/dev-session?access_token=...&refresh_token=...`). Navigate the Chrome tab to that URL. Wait for redirect to `/`. Take a screenshot to confirm login succeeded — you should see the "Overview" heading.

### 3. Verify Overview Page (`/`)

Navigate to `http://localhost:3000/` if not already there. Validate:

- Page has "Overview" heading (h1)
- Subtitle: "Your API usage at a glance"
- UsageBar present: shows plan tier badge, credits progress bar, "Pay as you go" toggle
- API Keys section: "API Keys" sub-heading with keys table and "Create Key" button

Take a screenshot. Record pass/fail.

### 4. Verify Playground Page (`/playground`)

Navigate to `http://localhost:3000/playground`. Validate:

- Page has "API Playground" heading (h1)
- Subtitle: "Test API endpoints and see generated code"
- **Left panel (form)**: API Key selector dropdown, "Market Ticker" input field, "Send Request" button, "Try an example" link
- **Right panel (code)**: Shell tab visible, code block area

Then test the interactive flow:

- Click "Try an example" — verify the Market Ticker field populates with a value
- Verify the code panel updates with a curl command
- Click "Send Request" — wait for response (up to 10 seconds)
- Check Response tab appears with status badge and response time metadata
- Switch to Preview tab — check that an orderbook table renders

Take screenshots at key steps. Record pass/fail per check.

### 5. Verify Coverage Page (`/coverage`)

Navigate to `http://localhost:3000/coverage`. Validate:

- Page has "Coverage" heading
- Subtitle: "Discover which markets have data and where the gaps are"
- **Summary cards**: 4 cards in a row — Markets Tracked, Total Snapshots, Total Deltas, Date Range (with compact number formatting)
- **Search/filters**: Search input with "Search markets..." placeholder, status filter dropdown (All/Active/Settled)
- **Table**: Markets grouped under event headers, expanded by default
  - Event header rows show event ticker/title and market count badge
  - Market rows show: ticker with title below, coverage date range, snapshot/delta/trade counts, segment count with timeline bar
- **Timeline bars**: Colored segment blocks on muted background showing coverage segments

Then test interactions:

- Type a partial ticker in the search box — verify results filter after ~300ms debounce
- Select "Active" or "Settled" from the status filter — verify results update
- Click "Clear filters" — verify the full list returns
- Click a market row to expand — verify per-segment details appear (date ranges and counts)
- If pagination available: click next page, verify new results load

Take screenshots at key steps. Record pass/fail per check.

### 6. Verify API Keys Page (`/keys`)

Navigate to `http://localhost:3000/keys`. Validate:

- Page has "API Keys" heading (h1)
- Subtitle: "Manage your API keys for accessing KalshiBook data endpoints."
- "Create Key" button with Plus icon in header
- Keys table with columns: Name, Type, Usage, Key, Last Used, Options
- OR empty state with "No API keys yet" message and "Create your first key" button

Take a screenshot. Record pass/fail.

### 7. Verify Billing Page (`/billing`)

Navigate to `http://localhost:3000/billing`. Validate:

- Page has "Billing" heading (h1)
- Subtitle: "Manage your subscription and payment methods."
- PlanCard showing: "Current Plan" title, tier badge, credits usage with progress bar
- Billing details: next billing date, Pay-As-You-Go badge
- Action buttons: "Manage in Stripe" or "Upgrade to Project Plan" button

Take a screenshot. Record pass/fail.

### 8. Summary

Print a results table:

| Page | Status | Notes |
|------|--------|-------|
| Overview | pass/fail | details |
| Playground - Layout | pass/fail | details |
| Playground - Try Example | pass/fail | details |
| Playground - Send Request | pass/fail | details |
| Playground - Response/Preview | pass/fail | details |
| Coverage - Layout | pass/fail | details |
| Coverage - Search/Filter | pass/fail | details |
| Coverage - Expand Row | pass/fail | details |
| API Keys | pass/fail | details |
| Billing | pass/fail | details |

If any checks failed, list what was missing or unexpected so it can be investigated.
