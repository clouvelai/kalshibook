# Phase 5: Dashboard - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Self-service web UI for API key management, usage tracking, and billing management. Users can view/create/revoke API keys, see credit consumption, toggle PAYG, and access Stripe billing portal. No API playground, no advanced analytics, no settings page.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout & navigation
- Left sidebar navigation like Tavily's dashboard
- Sidebar pages for Phase 5: **Overview, API Keys, Billing, Documentation (external link)**
- Overview page is the landing page — shows everything at a glance (usage bar, keys table, PAYG toggle)
- Visual style: match Tavily closely — light theme, clean white background, rounded cards, subtle gradients, professional feel

### API key management
- Named keys — user provides a name when creating a key (e.g., "production", "testing")
- Every new account starts with a default "dev" key named "default" — auto-created on signup
- Key types exist (dev/prod) — Claude's discretion on whether types have functional differences or are cosmetic labels. Keep simple, easy to extend later.
- Show-once-mask-forever — full key displayed in a copy-able modal on creation, then always masked in the table
- Keys table columns: Name, Type, Usage (per-key credits), Key (masked), Options (copy/edit/delete)
- Revoke confirmation: standard confirmation dialog ("Are you sure? This key will stop working immediately.")
- Per-key usage tracking visible in the keys table

### Usage & billing display
- Simple progress bar for credits like Tavily (credits used / credits available)
- PAYG toggle on the Overview page (below usage bar), matching existing POST /billing/payg endpoint
- Dedicated Billing page shows: current plan info, next billing date, payment method summary, then a "Manage in Stripe" button linking to Stripe Customer Portal
- Per-key usage breakdown in the keys table (which key consumed how many credits)

### Auth & login flow
- Email/password + Google OAuth for login/signup
- Supabase GoTrue handles auth (already built for API, extend to dashboard)
- Separate /login and /signup pages with KalshiBook branding
- First-time experience: just show the dashboard — default dev key is already there, usage at 0/1000

### Claude's Discretion
- Frontend framework choice (React, Next.js, etc.)
- Component library / CSS approach
- Key type functional differences (rate limits, etc.) — keep simple
- Exact spacing, typography, and color palette (match Tavily's aesthetic)
- Error states and loading skeletons
- Mobile responsiveness approach

</decisions>

<specifics>
## Specific Ideas

- "I want it to follow Tavily's example" — Tavily dashboard is the primary visual reference
- Overview page layout: plan name at top, usage bar, PAYG toggle, then API keys table — mirrors Tavily's Overview exactly
- Keys table with Name/Type/Usage/Key/Options columns — matches Tavily's API Keys section
- Tavily screenshot saved as reference: Screenshot 2026-02-15 at 5.54.34 PM.png

</specifics>

<deferred>
## Deferred Ideas

- **API Playground** — interactive request builder with code snippets (Python/JS/Shell), "Try an example" functionality, response viewer. Tavily's playground screenshot captured as reference. Belongs in a subsequent dashboard milestone.
- **Settings page** — account settings, preferences. Add when needed.
- **Use Cases / Certification pages** — Tavily has these, not applicable to KalshiBook currently.

</deferred>

---

*Phase: 05-dashboard*
*Context gathered: 2026-02-15*
