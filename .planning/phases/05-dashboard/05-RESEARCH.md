# Phase 5: Dashboard - Research

**Researched:** 2026-02-15
**Domain:** Full-stack web dashboard (Next.js frontend + FastAPI backend extensions)
**Confidence:** HIGH

## Summary

Phase 5 adds a self-service web UI for API key management, usage tracking, and billing management. The dashboard is a Next.js App Router application living in a `dashboard/` directory at the project root, communicating with the existing FastAPI backend (port 8000) via REST calls authenticated with Supabase JWT tokens. The frontend uses shadcn/ui components styled with Tailwind CSS to match Tavily's clean, professional aesthetic.

The existing backend already provides most endpoints needed (auth signup/login, key CRUD, billing status, PAYG toggle, Stripe checkout/portal). The main backend gaps are: (1) a per-key usage aggregation endpoint for the keys table, (2) auto-creating a default "default" API key on signup, and (3) adding Google OAuth support to the Supabase auth proxy. The frontend is entirely new -- Next.js 15, App Router, @supabase/ssr for auth, shadcn/ui for components.

**Primary recommendation:** Use Next.js 15 (stable) with App Router, shadcn/ui (Radix primitives), @supabase/ssr for auth state management, and Tailwind CSS. Put the dashboard in a top-level `dashboard/` directory as a standalone Next.js app. Use `next.config.js` rewrites to proxy `/api/*` to the FastAPI backend, eliminating CORS issues in production.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Dashboard layout & navigation
- Left sidebar navigation like Tavily's dashboard
- Sidebar pages for Phase 5: **Overview, API Keys, Billing, Documentation (external link)**
- Overview page is the landing page -- shows everything at a glance (usage bar, keys table, PAYG toggle)
- Visual style: match Tavily closely -- light theme, clean white background, rounded cards, subtle gradients, professional feel

#### API key management
- Named keys -- user provides a name when creating a key (e.g., "production", "testing")
- Every new account starts with a default "dev" key named "default" -- auto-created on signup
- Key types exist (dev/prod) -- Claude's discretion on whether types have functional differences or are cosmetic labels. Keep simple, easy to extend later.
- Show-once-mask-forever -- full key displayed in a copy-able modal on creation, then always masked in the table
- Keys table columns: Name, Type, Usage (per-key credits), Key (masked), Options (copy/edit/delete)
- Revoke confirmation: standard confirmation dialog ("Are you sure? This key will stop working immediately.")
- Per-key usage tracking visible in the keys table

#### Usage & billing display
- Simple progress bar for credits like Tavily (credits used / credits available)
- PAYG toggle on the Overview page (below usage bar), matching existing POST /billing/payg endpoint
- Dedicated Billing page shows: current plan info, next billing date, payment method summary, then a "Manage in Stripe" button linking to Stripe Customer Portal
- Per-key usage breakdown in the keys table (which key consumed how many credits)

#### Auth & login flow
- Email/password + Google OAuth for login/signup
- Supabase GoTrue handles auth (already built for API, extend to dashboard)
- Separate /login and /signup pages with KalshiBook branding
- First-time experience: just show the dashboard -- default dev key is already there, usage at 0/1000

### Claude's Discretion
- Frontend framework choice (React, Next.js, etc.)
- Component library / CSS approach
- Key type functional differences (rate limits, etc.) -- keep simple
- Exact spacing, typography, and color palette (match Tavily's aesthetic)
- Error states and loading skeletons
- Mobile responsiveness approach

### Deferred Ideas (OUT OF SCOPE)
- **API Playground** -- interactive request builder with code snippets (Python/JS/Shell), "Try an example" functionality, response viewer. Belongs in a subsequent dashboard milestone.
- **Settings page** -- account settings, preferences. Add when needed.
- **Use Cases / Certification pages** -- not applicable to KalshiBook currently.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.x (stable) | React framework with App Router, SSR, file-based routing | Industry standard for React dashboards; App Router is stable and mature; v15 is production-ready as of Feb 2026 |
| React | 19.x | UI library | Bundled with Next.js 15; required for shadcn/ui components |
| shadcn/ui | latest (Radix) | Component library -- sidebar, table, progress, dialog, button, card, etc. | Copy-paste components, full ownership, Tailwind-native styling, built-in Sidebar component matches Tavily layout |
| Tailwind CSS | 4.x | Utility-first CSS | Default with shadcn/ui; enables rapid Tavily-style styling |
| @supabase/ssr | 0.8.x | SSR-safe Supabase auth (cookie-based sessions) | Official Supabase package for Next.js App Router auth; replaces deprecated auth-helpers |
| @supabase/supabase-js | 2.x | Supabase client for auth operations | Required by @supabase/ssr; used for signInWithPassword, signInWithOAuth, signUp |
| TypeScript | 5.x | Type safety | Standard for Next.js projects; catches errors at build time |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-table | 8.x | Headless table logic (sorting, pagination) | Keys table with sorting/filtering |
| lucide-react | latest | Icon library | Sidebar icons, action buttons, copy/delete icons |
| sonner | latest | Toast notifications | Success/error feedback for key creation, deletion, PAYG toggle |
| clsx + tailwind-merge | latest | Conditional class merging | shadcn/ui utility (cn function) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Next.js 15 | Next.js 16 | v16 is newer but v15 is more battle-tested for production; v15.5 is the latest stable with all needed features |
| shadcn/ui (Radix) | shadcn/ui (Base UI) | Base UI support is new (Jan 2026); Radix is more mature and better documented |
| @tanstack/react-table | Simple HTML table | Fine for <20 rows; TanStack adds sorting/pagination for free |
| Tailwind CSS | Chakra UI (Tavily uses Chakra) | Tavily uses Chakra, but shadcn/ui is Tailwind-native; matching Tavily's *look* doesn't require matching their stack |

**Installation:**
```bash
npx create-next-app@15 dashboard --typescript --tailwind --eslint --app --src-dir
cd dashboard
npx shadcn@latest init
npx shadcn@latest add sidebar table progress dialog button card input label badge switch alert-dialog dropdown-menu separator skeleton toast
npm install @supabase/supabase-js @supabase/ssr @tanstack/react-table lucide-react sonner
```

## Architecture Patterns

### Recommended Project Structure
```
dashboard/                     # Next.js 15 app (separate from Python backend)
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout (fonts, metadata)
│   │   ├── (auth)/            # Route group for auth pages (no sidebar)
│   │   │   ├── layout.tsx     # Auth layout (centered card, branding)
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── signup/
│   │   │   │   └── page.tsx
│   │   │   └── auth/
│   │   │       └── callback/
│   │   │           └── route.ts   # OAuth callback handler
│   │   └── (dashboard)/       # Route group for authenticated pages (sidebar)
│   │       ├── layout.tsx     # Dashboard layout (SidebarProvider + Sidebar)
│   │       ├── page.tsx       # Overview page (redirects or serves as landing)
│   │       ├── overview/
│   │       │   └── page.tsx   # Overview: usage bar, PAYG toggle, keys summary
│   │       ├── keys/
│   │       │   └── page.tsx   # API Keys management page
│   │       └── billing/
│   │           └── page.tsx   # Billing page: plan info, Stripe portal link
│   ├── components/
│   │   ├── ui/                # shadcn/ui generated components
│   │   ├── sidebar/
│   │   │   └── app-sidebar.tsx
│   │   ├── keys/
│   │   │   ├── keys-table.tsx
│   │   │   ├── create-key-dialog.tsx
│   │   │   └── revoke-key-dialog.tsx
│   │   ├── billing/
│   │   │   ├── usage-bar.tsx
│   │   │   ├── payg-toggle.tsx
│   │   │   └── plan-card.tsx
│   │   └── auth/
│   │       ├── login-form.tsx
│   │       └── signup-form.tsx
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts      # createBrowserClient
│   │   │   ├── server.ts      # createServerClient
│   │   │   └── middleware.ts  # Token refresh logic
│   │   └── api.ts             # Typed fetch wrapper for FastAPI backend
│   └── types/
│       └── api.ts             # TypeScript types matching FastAPI models
├── next.config.ts
├── middleware.ts              # Supabase auth middleware (token refresh)
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### Pattern 1: Route Groups for Auth vs Dashboard Layout
**What:** Use Next.js route groups `(auth)` and `(dashboard)` to apply different layouts without affecting URL paths.
**When to use:** Always -- auth pages need a centered card layout; dashboard pages need the sidebar layout.
**Example:**
```typescript
// src/app/(auth)/layout.tsx
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}

// src/app/(dashboard)/layout.tsx
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/sidebar/app-sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1 p-6">{children}</main>
    </SidebarProvider>
  );
}
```

### Pattern 2: Supabase Auth Middleware for Token Refresh
**What:** Next.js middleware intercepts every request to refresh Supabase auth tokens stored in cookies.
**When to use:** Every request -- ensures server components always have fresh tokens.
**Example:**
```typescript
// middleware.ts
import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll(); },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  // Redirect unauthenticated users to login (except auth pages)
  if (!user && !request.nextUrl.pathname.startsWith("/login")
      && !request.nextUrl.pathname.startsWith("/signup")
      && !request.nextUrl.pathname.startsWith("/auth")) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

### Pattern 3: Typed API Client for FastAPI Backend
**What:** A thin fetch wrapper that adds auth headers and types responses from the FastAPI backend.
**When to use:** Every dashboard component that needs backend data.
**Example:**
```typescript
// src/lib/api.ts
import { createClient } from "@/lib/supabase/client";

const API_BASE = "/api"; // Proxied to FastAPI via next.config.ts rewrites

async function fetchAPI<T>(path: string, options: RequestInit = {}): Promise<T> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(session?.access_token && {
        Authorization: `Bearer ${session.access_token}`,
      }),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.error?.message || "API request failed");
  }

  return res.json();
}

// Typed API methods
export const api = {
  keys: {
    list: () => fetchAPI<{ data: ApiKeyInfo[]; request_id: string }>("/keys"),
    create: (name: string) =>
      fetchAPI<{ data: ApiKeyCreated; request_id: string }>("/keys", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    revoke: (keyId: string) =>
      fetchAPI<{ message: string }>(`/keys/${keyId}`, { method: "DELETE" }),
  },
  billing: {
    status: () => fetchAPI<BillingStatusResponse>("/billing/status"),
    togglePayg: (enable: boolean) =>
      fetchAPI<PaygToggleResponse>("/billing/payg", {
        method: "POST",
        body: JSON.stringify({ enable }),
      }),
    createCheckout: () =>
      fetchAPI<CheckoutResponse>("/billing/checkout", { method: "POST" }),
    createPortal: () =>
      fetchAPI<PortalResponse>("/billing/portal", { method: "POST" }),
  },
};
```

### Pattern 4: API Proxy via Next.js Rewrites
**What:** next.config.ts rewrites proxy `/api/*` to the FastAPI backend, avoiding CORS issues.
**When to use:** Always -- keeps frontend and backend communication clean.
**Example:**
```typescript
// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
```

### Pattern 5: Show-Once Key Modal
**What:** After creating a key, display the raw key in a modal with a copy button. The key is never stored in state or shown again.
**When to use:** POST /keys response handling.
**Example:**
```typescript
// Pseudocode for create-key-dialog.tsx
const [newKey, setNewKey] = useState<string | null>(null);

async function handleCreate(name: string) {
  const result = await api.keys.create(name);
  setNewKey(result.data.key); // Show in modal
  // After modal closes, key is gone forever
}

// Modal shows:
// "Your API key has been created. Copy it now -- you won't be able to see it again."
// [kb-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]  [Copy]
```

### Anti-Patterns to Avoid
- **Storing raw API keys in frontend state/localStorage:** The raw key should only exist in the creation response modal. Once dismissed, it's gone.
- **Using getSession() for server-side auth checks:** Always use getUser() (which validates the JWT). getSession() reads cookies without cryptographic verification.
- **Making API calls directly to port 8000 from the browser:** Use the Next.js rewrite proxy. Direct calls expose the backend URL and create CORS dependencies.
- **Creating a custom auth system:** Supabase GoTrue already handles signup, login, OAuth, JWT issuance, and token refresh. Don't rebuild any of this.
- **Putting the Next.js app inside the Python `src/` directory:** Keep it at the repo root as a sibling to `src/`. Python and Node.js have different toolchains.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Authentication/sessions | Custom JWT handling, cookie management | @supabase/ssr + middleware | Token refresh, cookie rotation, PKCE flow are security-critical |
| Sidebar navigation | Custom collapsible sidebar | shadcn/ui Sidebar component | Built-in state management, keyboard shortcuts, cookie persistence, mobile support |
| Data tables | Custom table with sorting | @tanstack/react-table + shadcn Table | Sorting, pagination, column visibility are solved problems |
| Toast notifications | Custom notification system | sonner (or shadcn toast) | Accessible, animated, auto-dismissing |
| Form validation | Manual validation | React Hook Form or native HTML validation | Consistent error handling, accessibility |
| CSS utility merging | Manual className concatenation | clsx + tailwind-merge (cn function) | Prevents Tailwind class conflicts |
| OAuth flow | Custom OAuth redirect handling | Supabase signInWithOAuth + callback route | PKCE flow, state management, nonce handling |

**Key insight:** This phase is mostly UI assembly -- wiring existing backend endpoints to UI components. Almost every technical problem (auth, tables, sidebar, progress bars, modals) has a high-quality off-the-shelf solution. The effort is in layout, styling to match Tavily, and integration testing.

## Common Pitfalls

### Pitfall 1: Supabase Token Refresh Race Condition
**What goes wrong:** Server components read a stale token from cookies, leading to 401s on the FastAPI backend. The user appears randomly "logged out."
**Why it happens:** Next.js server components can't write cookies. If the middleware doesn't refresh the token before the server component reads it, the component gets an expired JWT.
**How to avoid:** Always call `supabase.auth.getUser()` in the middleware, which triggers token refresh. The middleware pattern in this research handles this correctly.
**Warning signs:** Intermittent 401 errors after ~1 hour of inactivity (JWT expiry is 3600s in supabase config).

### Pitfall 2: OAuth Callback Route Missing
**What goes wrong:** Google OAuth redirects to `/auth/callback?code=...` but there's no route handler, resulting in a 404.
**Why it happens:** The PKCE flow requires a server-side route to exchange the authorization code for a session. This is easy to forget.
**How to avoid:** Create `src/app/(auth)/auth/callback/route.ts` that calls `supabase.auth.exchangeCodeForSession(code)` and redirects to the dashboard.
**Warning signs:** Google login redirects to a blank page or 404.

### Pitfall 3: Key Type Column Without Backend Support
**What goes wrong:** The UI shows a "Type" column (dev/prod) but the `api_keys` table has no `type` column, causing mismatched data.
**Why it happens:** The context mentions key types exist, but the current schema only has `name`, `key_hash`, `key_prefix`, `rate_limit`.
**How to avoid:** Add a `key_type` column to the `api_keys` table via migration before building the UI. Keep it simple -- a TEXT column with CHECK constraint for 'dev' or 'prod', defaulting to 'dev'.
**Warning signs:** UI shows "undefined" or empty in the Type column.

### Pitfall 4: Per-Key Usage Query Performance
**What goes wrong:** Aggregating credits from `api_key_usage` table is slow because there's no summary/materialized view -- every key list request scans the full usage table.
**Why it happens:** The `api_key_usage` table is append-only with every API request logged. For active users, this table grows fast.
**How to avoid:** Add a backend endpoint that aggregates per-key usage with a time-bounded query (current billing cycle only). Use the existing `billing_cycle_start` from `billing_accounts` to scope the query. Consider adding a `credits_used` counter column to `api_keys` for O(1) lookups if needed.
**Warning signs:** Key list endpoint takes >500ms; increases over time.

### Pitfall 5: Mismatched Auth for Dashboard vs API
**What goes wrong:** The dashboard uses Supabase browser auth (cookies via @supabase/ssr), but the FastAPI backend expects `Authorization: Bearer <jwt>` headers. The two auth mechanisms don't automatically align.
**Why it happens:** @supabase/ssr stores auth in httpOnly cookies for SSR. But fetch() calls to the FastAPI backend need the JWT extracted from the Supabase session and placed in an Authorization header.
**How to avoid:** The API client (`lib/api.ts`) must always call `supabase.auth.getSession()` to get the current access token and add it as a Bearer header. The Next.js rewrite proxy forwards this header to FastAPI.
**Warning signs:** Dashboard loads but all API calls return 401.

### Pitfall 6: Signup Without Default Key Creation
**What goes wrong:** User signs up, sees the dashboard, but the keys table is empty. The context says "default dev key is already there."
**Why it happens:** The current `POST /auth/signup` endpoint creates the Supabase user but does NOT create an API key or billing account. These are lazily created on first API request.
**How to avoid:** After successful signup, the backend should auto-create a default API key named "default" with type "dev". This could be done in the signup route handler or via a Supabase database trigger.
**Warning signs:** New user sees empty keys table instead of a default key.

## Code Examples

### Backend: Per-Key Usage Aggregation Endpoint (NEW)
```python
# New endpoint needed: GET /keys/usage
# Returns per-key credit usage for the current billing cycle

@router.get("/keys/usage")
async def get_keys_usage(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get per-key usage for the current billing cycle."""
    request_id = getattr(request.state, "request_id", "")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                ak.id,
                ak.name,
                ak.key_prefix,
                ak.created_at,
                ak.last_used_at,
                COALESCE(SUM(aku.credits_charged), 0) AS credits_used
            FROM api_keys ak
            LEFT JOIN api_key_usage aku ON aku.api_key_id = ak.id
                AND aku.created_at >= (
                    SELECT billing_cycle_start
                    FROM billing_accounts
                    WHERE user_id = $1
                )
            WHERE ak.user_id = $1 AND ak.revoked_at IS NULL
            GROUP BY ak.id, ak.name, ak.key_prefix, ak.created_at, ak.last_used_at
            ORDER BY ak.created_at DESC
            """,
            user["user_id"],
        )

    return {
        "data": [dict(row) for row in rows],
        "request_id": request_id,
    }
```

### Backend: Auto-Create Default Key on Signup (NEW)
```python
# In src/api/routes/auth.py, after successful signup:

from src.api.services.auth import create_api_key
from src.api.services.billing import ensure_billing_account

@router.post("/auth/signup", response_model=AuthResponse)
async def signup(body: SignupRequest, request: Request):
    supabase = request.app.state.supabase
    pool = request.app.state.pool
    result = await supabase.auth_sign_up(body.email, body.password)

    # Auto-provision: billing account + default API key
    user_id = result["user_id"]
    await ensure_billing_account(pool, user_id)
    await create_api_key(pool, user_id, name="default")

    return AuthResponse(...)
```

### Backend: Google OAuth Config for Supabase (NEW)
```toml
# supabase/config.toml addition
[auth.external.google]
enabled = true
client_id = "env(GOOGLE_OAUTH_CLIENT_ID)"
secret = "env(GOOGLE_OAUTH_CLIENT_SECRET)"
redirect_uri = ""
skip_nonce_check = false
```

### Frontend: OAuth Callback Route Handler
```typescript
// src/app/(auth)/auth/callback/route.ts
import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/";

  if (code) {
    const cookieStore = await cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
      {
        cookies: {
          getAll() { return cookieStore.getAll(); },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          },
        },
      }
    );

    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // Auth error -- redirect to login with error
  return NextResponse.redirect(`${origin}/login?error=auth_failed`);
}
```

### Frontend: Usage Progress Bar Component
```typescript
// src/components/billing/usage-bar.tsx
"use client";

import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface UsageBarProps {
  creditsUsed: number;
  creditsTotal: number;
  tier: string;
}

export function UsageBar({ creditsUsed, creditsTotal, tier }: UsageBarProps) {
  const percentage = Math.min((creditsUsed / creditsTotal) * 100, 100);
  const remaining = Math.max(creditsTotal - creditsUsed, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          API Usage — {tier.charAt(0).toUpperCase() + tier.slice(1)} Plan
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <Progress value={percentage} className="h-3" />
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>{creditsUsed.toLocaleString()} credits used</span>
            <span>{remaining.toLocaleString()} remaining</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

## Existing Backend API Surface (What Already Exists)

The dashboard will consume these existing endpoints, all requiring Supabase JWT auth:

| Endpoint | Method | Purpose | Dashboard Usage |
|----------|--------|---------|-----------------|
| `POST /auth/signup` | POST | Create user account | Signup page |
| `POST /auth/login` | POST | Email/password login | Login page |
| `GET /keys` | GET | List user's API keys | Keys table |
| `POST /keys` | POST | Create new API key | Create key dialog |
| `DELETE /keys/{id}` | DELETE | Revoke an API key | Revoke confirmation dialog |
| `GET /billing/status` | GET | Credit usage, tier, PAYG status | Overview page usage bar |
| `POST /billing/payg` | POST | Toggle PAYG billing | PAYG toggle switch |
| `POST /billing/checkout` | POST | Stripe Checkout URL | Upgrade button (billing page) |
| `POST /billing/portal` | POST | Stripe Customer Portal URL | "Manage in Stripe" button |

### New Endpoints Needed

| Endpoint | Method | Purpose | Why |
|----------|--------|---------|-----|
| `GET /keys/usage` | GET | Per-key credit aggregation for current billing cycle | Keys table "Usage" column; no existing endpoint provides this |
| `POST /auth/signup` (modified) | POST | Auto-create default key + billing account | First-time experience requires key to exist on signup |
| `POST /auth/google` or use Supabase client-side | - | Google OAuth | New auth method; may be handled entirely client-side via Supabase JS |

## Backend Schema Changes Needed

### New column: `api_keys.key_type`
```sql
ALTER TABLE api_keys ADD COLUMN key_type TEXT NOT NULL DEFAULT 'dev'
    CHECK (key_type IN ('dev', 'prod'));
```

**Recommendation on key type functional differences:** Keep types as cosmetic labels for now. Both dev and prod keys share the same rate limit (from the existing `rate_limit` column, default 100). This makes the feature easy to extend later (e.g., different rate limits per type) without breaking existing behavior. The column exists for display and future use.

## Supabase Auth Configuration for Google OAuth

The current `supabase/config.toml` does not have Google OAuth enabled. Required changes:

1. Add `[auth.external.google]` section to `supabase/config.toml` with `enabled = true`
2. Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` environment variables
3. Configure Google Cloud Console:
   - Authorized JavaScript origins: `http://localhost:3000` (dev), production URL
   - Authorized redirect URIs: `http://127.0.0.1:54321/auth/v1/callback` (local Supabase)
4. Add to `.env.example`: `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`

**Important:** For Google OAuth, the auth flow is handled client-side by `@supabase/supabase-js` calling `signInWithOAuth({ provider: 'google' })`. This redirects the browser to Google, then back to Supabase's `/auth/v1/callback`, then to the app's `/auth/callback` route handler which exchanges the code for a session. The FastAPI backend is NOT involved in the OAuth flow -- Supabase GoTrue handles it entirely.

## Frontend Environment Variables

```bash
# dashboard/.env.local
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<supabase-anon-key>
```

Note: The `NEXT_PUBLIC_` prefix makes these available in browser code. Only the anon/publishable key is exposed client-side -- never the service role key.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| @supabase/auth-helpers-nextjs | @supabase/ssr | 2024 | Old package deprecated; use @supabase/ssr for cookie-based auth |
| Next.js Pages Router | Next.js App Router | 2023 (stable) | Server components, route groups, nested layouts |
| getSession() for server auth | getUser() / getClaims() | 2024 | getSession reads cookies without JWT validation; security risk |
| shadcn/ui (Radix only) | shadcn/ui (Radix or Base UI) | Jan 2026 | Can now choose primitive library; Radix is more mature |
| Manual sidebar | shadcn/ui Sidebar component | 2024 | Built-in collapsible, mobile support, cookie persistence |

**Deprecated/outdated:**
- `@supabase/auth-helpers-nextjs`: Use `@supabase/ssr` instead. auth-helpers is no longer maintained.
- `supabase.auth.getSession()` for server-side validation: Use `supabase.auth.getUser()` which cryptographically validates the JWT.

## Open Questions

1. **Per-key usage: counter column vs. aggregation query?**
   - What we know: The `api_key_usage` table logs every request. Aggregation query works for low volume.
   - What's unclear: At high usage, will the aggregation query be fast enough? The table could grow to millions of rows.
   - Recommendation: Start with the aggregation query (bounded by billing_cycle_start). If performance becomes an issue, add a `credits_used_cycle` counter column to `api_keys` table and increment atomically on each request. This is a performance optimization that can be deferred.

2. **Google OAuth: default key auto-creation timing**
   - What we know: Email/password signup goes through `POST /auth/signup` where we can auto-create the key. Google OAuth signup happens through Supabase directly -- our backend doesn't have a hook.
   - What's unclear: How to auto-create the default key for Google OAuth users.
   - Recommendation: Use a "lazy initialization" pattern -- on first dashboard load after any login/signup, check if the user has any keys. If not, call `POST /keys` with name="default" from the frontend. This works for both email and OAuth signup flows without requiring a backend hook.

3. **Next.js deployment target**
   - What we know: Development uses `next dev` on port 3000 with rewrite proxy to FastAPI on port 8000.
   - What's unclear: Production deployment (Vercel? Self-hosted? Same server as FastAPI?).
   - Recommendation: Design for flexibility. The rewrite proxy pattern works for both Vercel (with env-based destination URLs) and self-hosted (nginx reverse proxy). Don't couple the frontend to the backend deployment.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/api/routes/auth.py`, `src/api/routes/keys.py`, `src/api/routes/billing.py`, `src/api/services/auth.py`, `src/api/services/billing.py`, `src/api/models.py`, `src/api/deps.py`, `src/shared/config.py`
- Existing schema: `supabase/migrations/20260214000001_create_api_keys.sql`, `20260215000001_create_billing_accounts.sql`, `20260215000002_create_api_key_usage.sql`
- Supabase config: `supabase/config.toml` (auth settings, Google OAuth template)
- [Supabase SSR Auth for Next.js](https://supabase.com/docs/guides/auth/server-side/nextjs) -- middleware pattern, token refresh
- [Supabase SSR Client Creation](https://supabase.com/docs/guides/auth/server-side/creating-a-client) -- browser + server client setup
- [Supabase Google OAuth](https://supabase.com/docs/guides/auth/social-login/auth-google) -- config.toml setup, signInWithOAuth
- [shadcn/ui Sidebar](https://ui.shadcn.com/docs/components/radix/sidebar) -- sidebar component API, SidebarProvider, useSidebar hook
- [shadcn/ui Progress](https://ui.shadcn.com/docs/components/radix/progress) -- progress bar component
- [shadcn/ui Data Table](https://ui.shadcn.com/docs/components/radix/data-table) -- TanStack table integration

### Secondary (MEDIUM confidence)
- [Next.js 15 stable features](https://nextjs.org/blog/next-15) -- App Router, Turbopack, React 19 support
- [shadcn/ui changelog](https://ui.shadcn.com/docs/changelog) -- Base UI support, RTL, visual builder
- [Vercel Next.js + shadcn/ui dashboard template](https://vercel.com/templates/next.js/next-js-and-shadcn-ui-admin-dashboard) -- reference implementation

### Tertiary (LOW confidence)
- Tavily dashboard visual reference (observed via WebFetch: uses Chakra UI, Plus Jakarta Sans font, Next.js, blue accent #3965FF, off-white background #fdfeff) -- structural reference only, we're using shadcn/ui not Chakra

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Next.js 15 + shadcn/ui + @supabase/ssr is the dominant pattern for this type of dashboard in 2026, verified across official docs
- Architecture: HIGH -- Route groups, middleware auth, rewrite proxy are all documented Next.js patterns; existing backend API surface is well-understood from codebase analysis
- Pitfalls: HIGH -- Token refresh, OAuth callback, schema gaps identified from direct codebase inspection
- Backend gaps: HIGH -- Identified from comparing CONTEXT.md requirements against existing endpoints and schema

**Research date:** 2026-02-15
**Valid until:** 2026-03-15 (30 days -- stable ecosystem, no fast-moving dependencies)
