---
phase: 05-dashboard
plan: 02
subsystem: ui
tags: [nextjs, supabase-ssr, tailwind, shadcn-ui, typescript, react, oauth]

# Dependency graph
requires:
  - phase: 05-dashboard
    plan: 01
    provides: key_type column, /keys/usage endpoint, auto-provisioning on signup
  - phase: 02-api
    provides: FastAPI auth endpoints (POST /auth/signup, POST /auth/login)
  - phase: 03-billing
    provides: billing status, PAYG toggle, checkout, portal endpoints
provides:
  - Next.js 15 app with Supabase SSR auth middleware
  - Typed API client proxying to FastAPI backend
  - Login page (email/password + Google OAuth)
  - Signup page (email/password + Google OAuth)
  - OAuth callback route for code exchange
  - shadcn/ui component library (sidebar, table, progress, dialog, card, etc.)
affects: [05-03 overview page, 05-04 keys page, 05-05 billing page]

# Tech tracking
tech-stack:
  added: [next@15, @supabase/ssr, @supabase/supabase-js, @tanstack/react-table, lucide-react, sonner, shadcn/ui, tailwindcss@4]
  patterns:
    - "Supabase SSR auth: browser client for client components, server client for server components, middleware for token refresh"
    - "API proxy: Next.js rewrites /api/* to FastAPI at localhost:8000"
    - "Typed API client: namespaced api.keys/billing/auth methods with session-bearing Authorization header"
    - "Signup flow: FastAPI signup (provisions billing + default key) then Supabase signInWithPassword for browser session"

key-files:
  created:
    - dashboard/package.json
    - dashboard/next.config.ts
    - dashboard/middleware.ts
    - dashboard/src/lib/supabase/client.ts
    - dashboard/src/lib/supabase/server.ts
    - dashboard/src/lib/supabase/middleware.ts
    - dashboard/src/lib/api.ts
    - dashboard/src/types/api.ts
    - dashboard/src/app/(auth)/layout.tsx
    - dashboard/src/app/(auth)/login/page.tsx
    - dashboard/src/app/(auth)/signup/page.tsx
    - dashboard/src/app/(auth)/auth/callback/route.ts
    - dashboard/src/components/auth/login-form.tsx
    - dashboard/src/components/auth/signup-form.tsx
    - dashboard/.env.local.example
  modified:
    - dashboard/src/app/layout.tsx
    - dashboard/src/app/page.tsx
    - dashboard/.gitignore

key-decisions:
  - "Signup calls FastAPI first (provisions billing + key) then Supabase signInWithPassword to establish browser session"
  - "API proxy via Next.js rewrites eliminates CORS entirely -- no CORS config needed"
  - "shadcn/ui sonner used instead of deprecated toast component"
  - "LoginForm wrapped in Suspense for useSearchParams SSR compatibility"

patterns-established:
  - "Auth layout: centered card on gray-50 background, outside dashboard sidebar layout"
  - "Google OAuth: redirectTo points to /auth/callback which exchanges code for session"
  - "Error display: URL param errors (OAuth failures) shown inline in auth forms"

# Metrics
duration: 4min
completed: 2026-02-16
---

# Phase 5 Plan 2: Next.js Dashboard Scaffold with Auth Summary

**Next.js 15 app with Supabase SSR auth, API proxy to FastAPI, typed API client, and login/signup pages (email/password + Google OAuth)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-16T01:54:25Z
- **Completed:** 2026-02-16T01:58:47Z
- **Tasks:** 2
- **Files modified:** 42 created, 3 modified

## Accomplishments
- Scaffolded Next.js 15 app with TypeScript, Tailwind v4, and 18 shadcn/ui components
- Supabase SSR auth middleware redirects unauthenticated users to /login, refreshes tokens automatically
- API proxy via Next.js rewrites routes /api/* to FastAPI at localhost:8000
- Typed API client with namespaced methods for keys, billing, and auth endpoints
- Login page with email/password and Google OAuth, error display from URL params
- Signup page calls FastAPI signup endpoint (provisions billing + default key) then establishes Supabase browser session
- OAuth callback route exchanges authorization code for session

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js 15 project with Supabase SSR auth** - `fb57755` (feat)
2. **Task 2: Build login, signup, and OAuth callback pages** - `db9031e` (feat)

## Files Created/Modified
- `dashboard/package.json` - Next.js 15 project with all dependencies
- `dashboard/next.config.ts` - API proxy rewrites to FastAPI
- `dashboard/middleware.ts` - Root middleware importing Supabase updateSession
- `dashboard/src/lib/supabase/client.ts` - Browser client for client components
- `dashboard/src/lib/supabase/server.ts` - Server client with cookie handling
- `dashboard/src/lib/supabase/middleware.ts` - Auth middleware with token refresh and redirect logic
- `dashboard/src/lib/api.ts` - Typed fetch wrapper with namespaced API methods
- `dashboard/src/types/api.ts` - TypeScript interfaces matching FastAPI models
- `dashboard/src/app/layout.tsx` - Root layout with KalshiBook metadata and Toaster
- `dashboard/src/app/(auth)/layout.tsx` - Centered card auth layout
- `dashboard/src/app/(auth)/login/page.tsx` - Login page server component
- `dashboard/src/app/(auth)/signup/page.tsx` - Signup page server component
- `dashboard/src/app/(auth)/auth/callback/route.ts` - OAuth code exchange handler
- `dashboard/src/components/auth/login-form.tsx` - Login form with email/password + Google OAuth
- `dashboard/src/components/auth/signup-form.tsx` - Signup form with validation and dual-step auth

## Decisions Made
- Signup flow calls FastAPI first (to provision billing account + default key) then Supabase signInWithPassword to establish the browser session -- ensures user is fully provisioned before entering dashboard
- API proxy via Next.js rewrites eliminates CORS entirely -- no backend CORS configuration needed for the dashboard
- Used shadcn/ui sonner component instead of deprecated toast (shadcn CLI rejects toast in favor of sonner)
- LoginForm wrapped in Suspense boundary for useSearchParams SSR compatibility in Next.js 15
- .gitignore updated to allow .env.local.example through the .env* ignore pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] shadcn/ui toast component deprecated**
- **Found during:** Task 1 (dependency installation)
- **Issue:** shadcn CLI rejects `toast` component -- it is deprecated in favor of `sonner`
- **Fix:** Replaced `toast` with `sonner` in shadcn add command
- **Files modified:** dashboard/src/components/ui/sonner.tsx (created instead of toast.tsx)
- **Verification:** shadcn add succeeded, build passes
- **Committed in:** fb57755 (Task 1 commit)

**2. [Rule 3 - Blocking] .gitignore blocking .env.local.example**
- **Found during:** Task 1 (git staging)
- **Issue:** Default Next.js .gitignore has `.env*` pattern which blocks `.env.local.example` from being committed
- **Fix:** Added `!.env.local.example` exception to .gitignore
- **Files modified:** dashboard/.gitignore
- **Verification:** git add succeeds without -f flag
- **Committed in:** fb57755 (Task 1 commit)

**3. [Rule 2 - Missing Critical] Suspense boundary for useSearchParams**
- **Found during:** Task 2 (login page)
- **Issue:** Next.js 15 requires useSearchParams to be wrapped in Suspense for static generation compatibility
- **Fix:** Wrapped LoginForm in Suspense in the login page server component
- **Files modified:** dashboard/src/app/(auth)/login/page.tsx
- **Verification:** Build succeeds without "missing Suspense boundary" warning
- **Committed in:** db9031e (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 blocking)
**Impact on plan:** All auto-fixes necessary for correct build and deployment. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Supabase connection details go in `.env.local` (see `.env.local.example`).

## Next Phase Readiness
- Dashboard scaffold complete with auth, API client, and all shadcn/ui components
- Ready for Overview page (05-03): sidebar layout, usage bar, keys table, PAYG toggle
- Ready for API Keys page (05-04): key management UI using existing shadcn/ui table + dialog components
- Ready for Billing page (05-05): Stripe integration using existing API client methods

## Self-Check: PASSED

All 16 files verified present. Both task commits (fb57755, db9031e) verified in git log.

---
*Phase: 05-dashboard*
*Completed: 2026-02-16*
