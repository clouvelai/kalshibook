# Phase 6: API Playground - Research

**Researched:** 2026-02-16
**Domain:** Interactive API playground UI (Next.js dashboard extension)
**Confidence:** HIGH

## Summary

Phase 6 adds an interactive API playground page to the existing Next.js dashboard. Users configure request parameters in a form, see a live-updating curl command, execute requests against the backend, and view JSON responses -- all within a split-panel layout modeled after Tavily's playground. The page launches with a single endpoint: `POST /orderbook` (orderbook reconstruction).

The technical challenge is modest: this is primarily a frontend feature within the existing dashboard architecture. The playground page is a new route at `/playground` using existing patterns (client component, shadcn/ui components, Tailwind CSS). The two non-trivial aspects are: (1) syntax highlighting for the curl code block, which requires a new dependency (`prism-react-renderer`), and (2) the request execution flow, which must use the user's API key (not the Supabase JWT) to authenticate against the backend, requiring a new fetch utility separate from the existing `fetchAPI` wrapper.

The existing Next.js rewrite (`/api/*` -> `localhost:8000/*`) transparently forwards all headers, so playground requests can go through the same proxy path. The user's API key is obtained via the existing key reveal flow (`api.keys.reveal(keyId)`), and sent as `Authorization: Bearer kb-...` to the `/api/orderbook` endpoint.

**Primary recommendation:** Build as a single client component page with child components for form, code panel, and response panel. Use `prism-react-renderer` with the `vsDark` theme for syntax highlighting. Use the existing Next.js rewrite proxy for request execution -- no new Route Handler needed. Add shadcn/ui Tabs component for language tabs and Response/Code toggle.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Starting endpoint
- Launch with GET /markets/{ticker}/orderbook (the hero endpoint)
- market_ticker is the required field shown prominently
- Optional params (at timestamp, depth) go in collapsible "Additional fields" section -- matches Tavily pattern and scales as we add more endpoints later

#### Language tabs
- Shell tab active and functional
- Python and JavaScript tabs visible but disabled (grayed out styling)
- Hover tooltip on disabled tabs: "Coming soon"
- No click behavior on disabled tabs beyond the tooltip

#### Code panel
- Dark theme code block with syntax highlighting (match Tavily aesthetic)
- Copy button in top-right corner
- Curl command updates in real-time as form values change
- API key masked in generated curl: `X-API-Key: kb_live_****...****`
- Shell tab shows well-formatted multi-line curl with backslash continuations

#### Request execution
- Live execute from browser -- "Send Request" button fires the request through Next.js API proxy
- Request costs credits (same as direct API call)
- Full-width prominent "Send Request" button (like Tavily)

#### Response panel
- Toggles with Code panel via Response | Code tabs in top-right
- Two sub-tabs: JSON (syntax-highlighted, copyable) and Preview
- Response metadata shown (status code, response time, credits deducted)

#### API key selector
- Dropdown populated with user's API keys
- Auto-selects first/default key -- zero friction to first request
- Key displayed masked in dropdown (like Tavily: prefix visible, rest masked)

#### "Try an example"
- Hardcoded example with a representative market ticker and timestamp
- Pre-fills form fields when clicked
- Future milestone will add dynamic live market examples

#### Page layout
- Split panel: left = form config, right = code/response (like Tavily)
- Sidebar placement: after Overview, before API Keys -- second item, prominent position
- Mobile: form stacks on top, code/response below (vertical stack, scroll to see results)

### Claude's Discretion
- Preview sub-tab format for orderbook data (table, summary card, or hybrid)
- Response metadata presentation (inline header bar vs. separate section)
- Exact syntax highlighting theme and color choices
- Loading/spinner state during request execution
- Error state presentation (invalid params, auth failures, credit exhaustion)
- Empty state before first request is sent

### Deferred Ideas (OUT OF SCOPE)
- Python SDK tab -- requires client library (future milestone)
- JavaScript SDK tab -- requires client library (future milestone)
- Dynamic "live market" example selection -- separate milestone for curated demo data
- Additional endpoints beyond orderbook -- add incrementally after launch
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.x (already installed) | App Router, page routing | Already the dashboard framework |
| React | 19.x (already installed) | UI components | Already installed |
| shadcn/ui | latest (already installed) | Tabs, Select, Card, Button, Input, Label, Tooltip, Badge, Skeleton | Already the component library; Tabs component needs to be added via CLI |
| Tailwind CSS | 4.x (already installed) | Styling | Already configured |
| prism-react-renderer | 2.x | Syntax highlighting for curl and JSON code blocks | React-native, render-props API, bundled themes (vsDark), small footprint, no global namespace pollution. Used by Docusaurus and many React projects. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | latest (already installed) | Icons (Copy, Play, ChevronDown, Terminal, Code) | Button icons, tab icons |
| sonner | latest (already installed) | Toast notifications | "Copied to clipboard", error feedback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| prism-react-renderer | shiki / react-shiki | Shiki produces more accurate VS Code-quality highlighting and works well with RSC, but it's async and heavier. prism-react-renderer is simpler for client-side use, lighter, and sufficient for bash/JSON highlighting. |
| prism-react-renderer | highlight.js | highlight.js is lightweight and supports Next.js SSG well, but it's not React-native and requires manual DOM integration. prism-react-renderer provides a clean React API. |
| prism-react-renderer | react-syntax-highlighter | react-syntax-highlighter is popular but poorly maintained, has known bugs with Next.js and Tailwind CSS, and is larger. prism-react-renderer is actively maintained and from a reputable source (Formidable). |

**Installation:**
```bash
cd dashboard && npm install prism-react-renderer
npx shadcn@latest add tabs
```

## Architecture Patterns

### Recommended Project Structure
```
dashboard/src/
├── app/(dashboard)/
│   └── playground/
│       └── page.tsx              # Playground page (client component)
├── components/
│   ├── playground/
│   │   ├── playground-form.tsx   # Left panel: form inputs, key selector, send button
│   │   ├── code-panel.tsx        # Right panel: language tabs + syntax-highlighted curl
│   │   ├── response-panel.tsx    # Right panel: JSON response + Preview + metadata
│   │   ├── orderbook-preview.tsx # Preview sub-tab rendering for orderbook data
│   │   └── use-playground.ts     # Custom hook: form state, curl generation, request execution
│   └── ui/
│       └── tabs.tsx              # shadcn/ui Tabs (added via CLI)
├── lib/
│   └── playground.ts             # Playground-specific fetch (API key auth, not JWT)
└── types/
    └── api.ts                    # Extended with OrderbookRequest/Response types
```

### Pattern 1: Playground State Hook
**What:** A custom hook (`usePlayground`) that manages all playground state -- form values, selected key, generated curl, request/response lifecycle, loading states.
**When to use:** The playground has interconnected state (form changes -> curl updates, send -> response display). A single hook keeps this coherent.
**Example:**
```typescript
// dashboard/src/components/playground/use-playground.ts
interface PlaygroundState {
  // Form fields
  marketTicker: string;
  timestamp: string;
  depth: string;

  // Key selection
  selectedKeyId: string;
  selectedKeyPrefix: string;
  revealedKey: string | null;  // Full key for request execution

  // Code generation
  curlCommand: string;

  // Request lifecycle
  isLoading: boolean;
  response: PlaygroundResponse | null;
  error: PlaygroundError | null;

  // Response metadata
  statusCode: number | null;
  responseTime: number | null;
  creditsDeducted: number | null;
}

export function usePlayground() {
  const [state, setState] = useState<PlaygroundState>(initialState);

  // Auto-generate curl when form values change
  useEffect(() => {
    const curl = generateCurl(state);
    setState(prev => ({ ...prev, curlCommand: curl }));
  }, [state.marketTicker, state.timestamp, state.depth]);

  // Execute request
  const sendRequest = async () => { /* ... */ };

  // Fill example
  const fillExample = () => { /* ... */ };

  return { ...state, sendRequest, fillExample, setField };
}
```

### Pattern 2: Curl Generation (Pure Function)
**What:** A pure function that builds a multi-line curl command from form state.
**When to use:** Called reactively whenever form values change.
**Example:**
```typescript
function generateCurl(params: {
  marketTicker: string;
  timestamp: string;
  depth: string;
  keyPrefix: string;
}): string {
  const lines = [
    `curl -X POST https://api.kalshibook.com/orderbook \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -H "Authorization: Bearer ${params.keyPrefix}****...****" \\`,
    `  -d '{`,
  ];

  const body: Record<string, unknown> = {
    market_ticker: params.marketTicker,
  };
  if (params.timestamp) body.timestamp = params.timestamp;
  if (params.depth) body.depth = parseInt(params.depth);

  lines.push(`    ${JSON.stringify(body, null, 4).split('\n').join('\n    ')}`);
  lines.push(`  }'`);

  return lines.join('\n');
}
```

### Pattern 3: Playground Fetch (API Key Auth)
**What:** A separate fetch function for playground requests that uses API key auth instead of Supabase JWT.
**When to use:** When executing playground requests. This is distinct from the existing `fetchAPI` in `lib/api.ts` which uses Supabase JWT.
**Example:**
```typescript
// dashboard/src/lib/playground.ts
export interface PlaygroundResult {
  data: unknown;
  status: number;
  responseTime: number;
  creditsDeducted: number | null;
  creditsRemaining: number | null;
  headers: Record<string, string>;
}

export async function executePlaygroundRequest(
  path: string,
  body: Record<string, unknown>,
  apiKey: string,
): Promise<PlaygroundResult> {
  const startTime = performance.now();

  const response = await fetch(`/api${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  const elapsed = performance.now() - startTime;
  const data = await response.json();

  return {
    data,
    status: response.status,
    responseTime: elapsed,
    creditsDeducted: response.headers.get('X-Credits-Cost')
      ? parseInt(response.headers.get('X-Credits-Cost')!)
      : null,
    creditsRemaining: response.headers.get('X-Credits-Remaining')
      ? parseInt(response.headers.get('X-Credits-Remaining')!)
      : null,
    headers: Object.fromEntries(response.headers.entries()),
  };
}
```

### Pattern 4: Code Block with Copy Button
**What:** Reusable code block component wrapping prism-react-renderer with a copy-to-clipboard button.
**When to use:** Both the curl display and the JSON response display need syntax-highlighted code with copy functionality.
**Example:**
```typescript
import { Highlight, themes } from 'prism-react-renderer';
import { Copy, Check } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language: string;
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative rounded-lg bg-[#1e1e1e] overflow-hidden">
      <button
        onClick={handleCopy}
        className="absolute top-3 right-3 ..."
      >
        {copied ? <Check /> : <Copy />}
      </button>
      <Highlight theme={themes.vsDark} code={code} language={language}>
        {({ style, tokens, getLineProps, getTokenProps }) => (
          <pre style={style} className="p-4 overflow-x-auto text-sm">
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })}>
                {line.map((token, key) => (
                  <span key={key} {...getTokenProps({ token })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </div>
  );
}
```

### Pattern 5: Split Panel Layout (Responsive)
**What:** Desktop shows side-by-side panels; mobile stacks vertically.
**When to use:** The main playground page layout.
**Example:**
```typescript
<div className="flex flex-col lg:flex-row gap-6">
  {/* Left panel: Form */}
  <div className="w-full lg:w-[400px] lg:shrink-0 space-y-6">
    <PlaygroundForm ... />
  </div>

  {/* Right panel: Code / Response */}
  <div className="flex-1 min-w-0">
    <CodeResponsePanel ... />
  </div>
</div>
```

### Anti-Patterns to Avoid
- **Don't use iframe/sandbox for request execution:** Execute requests directly via fetch from the client. The Next.js rewrite proxy handles CORS and routing. No need for a sandboxed environment.
- **Don't store the full API key in React state long-term:** Reveal the key when needed for execution, use it immediately, and keep it in component state only for the session. Don't persist to localStorage.
- **Don't create a new Next.js Route Handler for the proxy:** The existing `next.config.ts` rewrite already proxies `/api/*` to the FastAPI backend. The playground just needs to send requests with API key auth headers instead of JWT. No new server-side code is needed.
- **Don't make the curl command editable:** The curl is a read-only display generated from form inputs. Users modify the form, the curl updates reactively.

## Critical Implementation Detail: Endpoint Mismatch

**IMPORTANT:** The user's decision references "GET /markets/{ticker}/orderbook" but the actual backend endpoint is **`POST /orderbook`** with a JSON body containing `market_ticker`, `timestamp`, and `depth` fields. The playground must use the actual endpoint format:

```bash
curl -X POST https://api.kalshibook.com/orderbook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer kb-..." \
  -d '{
    "market_ticker": "KXBTC-25FEB14-T96074.99",
    "timestamp": "2025-02-14T18:00:00Z",
    "depth": 10
  }'
```

The form should present `market_ticker` as the prominent required field (matching the user's intent), with `timestamp` and `depth` as optional fields in a collapsible section. The generated curl reflects the actual POST body format.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Syntax highlighting | Custom regex tokenizer | `prism-react-renderer` | Proper tokenization of bash/JSON is complex; library handles edge cases, themes, and React integration |
| Tabs component | Custom tab switcher with state | shadcn/ui `Tabs` (Radix) | Keyboard navigation, ARIA attributes, focus management handled by Radix primitives |
| Select dropdown | Custom dropdown for key selector | shadcn/ui `Select` (already installed) | Accessibility, portal rendering, scroll handling |
| Tooltip | CSS-only tooltip for disabled tabs | shadcn/ui `Tooltip` (already installed) | Proper positioning, portal rendering, delay handling |
| Copy to clipboard | Custom clipboard API wrapper | `navigator.clipboard.writeText()` + sonner toast | Standard Web API, already used in keys-table.tsx |
| Collapsible section | Accordion from scratch | shadcn/ui `Collapsible` or simple `details/summary` | User wants a simple toggle for additional fields |

**Key insight:** The playground is a composition of existing patterns and components. The only truly new element is the syntax-highlighted code block, which is solved by `prism-react-renderer`. Everything else reuses dashboard infrastructure.

## Common Pitfalls

### Pitfall 1: API Key Reveal Race Condition
**What goes wrong:** User selects a key and immediately clicks "Send Request" before the key reveal API call completes. The request fires with no API key.
**Why it happens:** Key reveal is async (hits `/keys/{id}/reveal`). There's a gap between selecting a key and having the full key available.
**How to avoid:** Auto-reveal the first/default key on page load. Disable "Send Request" button until a key is revealed. Cache revealed keys in component state for the session.
**Warning signs:** Requests failing with 401 errors intermittently.

### Pitfall 2: prism-react-renderer Missing Language Support
**What goes wrong:** Bash/shell syntax not highlighted properly -- just rendered as plain text.
**Why it happens:** prism-react-renderer bundles only common languages by default. Bash may not be included in the default bundle.
**How to avoid:** Check if `bash` is in the default language list. If not, extend Prism with the bash grammar: `import "prismjs/components/prism-bash"`. JSON is included by default.
**Warning signs:** Code block renders with no color highlighting for bash commands.

### Pitfall 3: Curl Command XSS via User Input
**What goes wrong:** User enters a market ticker containing shell metacharacters (e.g., `'; rm -rf /`), and the generated curl displays it unsafely.
**Why it happens:** The curl is displayed in a code block (safe from HTML injection), but the display could be confusing. More importantly, the actual request uses fetch with a JSON body, so shell injection is impossible in execution.
**How to avoid:** The curl display is read-only UI, rendered via prism-react-renderer (which escapes HTML). The actual request sends JSON via fetch, never executes shell commands. No additional sanitization needed for the display. Input validation on the form fields (e.g., market_ticker regex pattern) prevents confusing display.
**Warning signs:** Strange characters appearing in the curl display.

### Pitfall 4: Response Headers Not Accessible
**What goes wrong:** Credit headers (`X-Credits-Remaining`, `X-Credits-Cost`) are not readable from the fetch response in the browser.
**Why it happens:** CORS restrictions can prevent reading custom response headers. The header must be listed in `Access-Control-Expose-Headers`.
**How to avoid:** The FastAPI backend already has `allow_headers=["*"]` in CORS config. However, `Access-Control-Expose-Headers` may not include the credit headers. The backend middleware adds these headers, but they may not be exposed to the browser. Check and add `Access-Control-Expose-Headers` to the CORS middleware if needed. Alternatively, read the credit info from the response body (the `response_time` field is already in the response body).
**Warning signs:** `response.headers.get('X-Credits-Cost')` returns null despite the backend sending the header.

### Pitfall 5: Stale Key List After Key Revocation
**What goes wrong:** User revokes a key on the API Keys page, navigates to Playground, and the revoked key is still in the dropdown.
**Why it happens:** Keys are fetched on page mount and not refreshed.
**How to avoid:** Fetch keys on every Playground page mount. This is a small API call and ensures fresh data. Consider a lightweight cache with short TTL if performance becomes a concern.
**Warning signs:** "Invalid API key" errors when using a key that appears in the dropdown.

### Pitfall 6: Large JSON Response Rendering Performance
**What goes wrong:** Orderbook responses with many price levels produce large JSON blobs. prism-react-renderer can be slow to tokenize and render thousands of lines.
**Why it happens:** prism-react-renderer processes every token synchronously. Large JSON responses (e.g., full depth orderbook with 99 yes + 99 no levels) can produce significant DOM.
**How to avoid:** Use the `depth` parameter in the example to limit response size. For very large responses, consider truncating the JSON display with a "Show full response" toggle. The `depth` field defaults to showing all levels, so the example should set `depth: 10` as a sensible default.
**Warning signs:** UI freeze or jank when rendering response.

## Code Examples

### Complete Curl Generation Function
```typescript
// Source: KalshiBook codebase patterns + Tavily playground reference
interface CurlParams {
  marketTicker: string;
  timestamp: string;
  depth: string;
  keyPrefix: string;
  baseUrl?: string;
}

export function generateCurlCommand(params: CurlParams): string {
  const url = params.baseUrl || 'https://api.kalshibook.com';

  const body: Record<string, unknown> = {
    market_ticker: params.marketTicker,
  };

  if (params.timestamp) {
    body.timestamp = params.timestamp;
  }
  if (params.depth && parseInt(params.depth) > 0) {
    body.depth = parseInt(params.depth);
  }

  const jsonBody = JSON.stringify(body, null, 2);
  const maskedKey = `${params.keyPrefix}${'*'.repeat(20)}`;

  return [
    `curl -X POST ${url}/orderbook \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -H "Authorization: Bearer ${maskedKey}" \\`,
    `  -d '${jsonBody}'`,
  ].join('\n');
}
```

### Key Selector with Auto-Reveal
```typescript
// Fetch keys on mount, auto-reveal first key
useEffect(() => {
  async function loadKeys() {
    const response = await api.keys.list();
    setKeys(response.data);

    if (response.data.length > 0) {
      const firstKey = response.data[0];
      setSelectedKeyId(firstKey.id);
      setSelectedKeyPrefix(firstKey.key_prefix);

      // Auto-reveal for execution readiness
      try {
        const revealed = await api.keys.reveal(firstKey.id);
        setRevealedKey(revealed.data.key);
      } catch {
        // Key reveal not available -- user will need to create a new key
      }
    }
  }
  loadKeys();
}, []);
```

### Hardcoded Example Data
```typescript
// Source: KalshiBook domain knowledge
const EXAMPLE = {
  marketTicker: 'KXBTC-25FEB14-T96074.99',
  timestamp: '2025-02-14T18:00:00Z',
  depth: '10',
} as const;

const fillExample = () => {
  setMarketTicker(EXAMPLE.marketTicker);
  setTimestamp(EXAMPLE.timestamp);
  setDepth(EXAMPLE.depth);
};
```

### prism-react-renderer with Bash Language Extension
```typescript
// If bash is not in default bundle, extend it:
import { Highlight, themes, Prism } from 'prism-react-renderer';

// Extend Prism with bash language support
(typeof globalThis !== "undefined" ? globalThis : window).Prism = Prism;
require("prismjs/components/prism-bash");

// Then use normally:
<Highlight theme={themes.vsDark} code={curlCommand} language="bash">
  {/* render function */}
</Highlight>
```

Note: prism-react-renderer v2 may already include bash in its default bundle. Verify during implementation by testing -- if bash highlighting works without the extension, skip the Prism extension step.

### Response Metadata Display
```typescript
// Recommendation: inline header bar above response content
function ResponseMetadata({ status, responseTime, creditsDeducted }: {
  status: number;
  responseTime: number;
  creditsDeducted: number | null;
}) {
  return (
    <div className="flex items-center gap-4 px-4 py-2 border-b bg-muted/50 text-sm">
      <Badge variant={status < 400 ? "secondary" : "destructive"}>
        {status}
      </Badge>
      <span className="text-muted-foreground">
        {responseTime.toFixed(0)}ms
      </span>
      {creditsDeducted !== null && (
        <span className="text-muted-foreground">
          {creditsDeducted} credits
        </span>
      )}
    </div>
  );
}
```

### Orderbook Preview Component (Discretion)
```typescript
// Recommendation: Side-by-side table for yes/no sides
function OrderbookPreview({ data }: { data: OrderbookResponse }) {
  return (
    <div className="grid grid-cols-2 gap-4 p-4">
      <div>
        <h4 className="text-sm font-medium mb-2 text-green-600">Yes</h4>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted-foreground">
              <th className="text-left">Price</th>
              <th className="text-right">Qty</th>
            </tr>
          </thead>
          <tbody>
            {data.yes.map((level, i) => (
              <tr key={i}>
                <td>{level.price}c</td>
                <td className="text-right">{level.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <h4 className="text-sm font-medium mb-2 text-red-600">No</h4>
        {/* Mirror structure for no side */}
      </div>
    </div>
  );
}
```

## Discretion Recommendations

### Preview Sub-tab Format
**Recommendation: Side-by-side orderbook table.** The orderbook data has a natural two-column structure (yes/no sides with price/quantity levels). A table presentation matches how traders think about orderbooks. Include a summary header showing market ticker, timestamp, snapshot basis, and deltas applied count. This is more useful than raw JSON for quick visual validation.

### Response Metadata Presentation
**Recommendation: Inline header bar.** A slim horizontal bar above the response content showing status badge, response time, and credits deducted. This matches Tavily's compact metadata display and doesn't waste vertical space. Use a Badge component for the status code (green for 2xx, red for 4xx/5xx).

### Syntax Highlighting Theme
**Recommendation: `vsDark` (default prism-react-renderer theme).** This is the VS Code dark theme, widely recognized by developers. It provides good contrast on a dark background (`#1e1e1e`) and is the default bundled theme, requiring zero configuration. Matches the "dark theme code block" decision.

### Loading/Spinner State
**Recommendation: Replace "Send Request" button text with a spinner and "Sending..." text during execution.** Disable the button to prevent double-sends. In the response panel, show a centered spinner with "Executing request..." text. This is the standard pattern used across the dashboard.

### Error State Presentation
**Recommendation: Display errors in the response panel as structured error JSON** (matching the actual API error response format: `{ error: { code, message, status }, request_id }`). Use the same syntax-highlighted JSON view but with a red status badge. For client-side errors (no key selected, missing required field), show an inline form validation message below the relevant field. For auth failures, show a toast + suggestion to check the API key.

### Empty State (Before First Request)
**Recommendation: Show a centered message in the response panel area** with a terminal icon, "Send a request to see the response" text, and a subtle prompt to try the example. This matches the pattern of the Keys page empty state.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-syntax-highlighter | prism-react-renderer 2.x | 2023 | prism-react-renderer is smaller, actively maintained, and React-native. react-syntax-highlighter has known SSR bugs. |
| Highlight.js for React | prism-react-renderer or Shiki | 2024-2025 | Highlight.js works but isn't React-native. prism-react-renderer provides a clean render-props API. Shiki is for RSC/SSR use cases. |
| Next.js middleware for proxy | Next.js rewrites (config) or proxy.js | 2025-2026 | Simple rewrites are sufficient for transparent proxying. Route Handlers only needed when request/response transformation is required. |
| defaultProps pattern (prism-react-renderer v1) | Named exports (v2) | 2023 | v2 uses `import { Highlight, themes } from 'prism-react-renderer'` -- no more `defaultProps` spreading |

**Deprecated/outdated:**
- `react-syntax-highlighter`: Popular but poorly maintained, known bugs with Next.js static generation and Tailwind CSS integration. Avoid.
- `prism-react-renderer` v1 API: v2 changed the import pattern. Use `{ Highlight, themes }` named exports, not default import with `defaultProps`.
- Next.js middleware for simple proxying: `proxy.js` (formerly `middleware.ts`) should not be used for simple API proxying. Use `rewrites` in `next.config.ts` (already configured).

## Open Questions

1. **prism-react-renderer bash support out-of-the-box**
   - What we know: The library bundles "common language syntaxes" by default, but the exact list varies by version. JSON is definitely included.
   - What's unclear: Whether `bash` or `shell` is in the default v2 bundle.
   - Recommendation: Test during implementation. If bash highlighting doesn't work, add the Prism bash grammar extension (3 lines of code). This is a minor implementation detail, not a planning blocker.

2. **CORS `Access-Control-Expose-Headers` for credit headers**
   - What we know: The FastAPI backend sets `allow_headers=["*"]` and `allow_origins=["*"]` in CORS middleware. The credit headers are added by custom middleware.
   - What's unclear: Whether `Access-Control-Expose-Headers` includes custom headers. By default, only CORS-safelisted headers are exposed to JavaScript.
   - Recommendation: Test during implementation. If credit headers aren't readable, add `expose_headers=["X-Credits-Remaining", "X-Credits-Used", "X-Credits-Total", "X-Credits-Cost", "X-Request-ID"]` to the FastAPI CORS middleware. Alternatively, read credit info from the response body (`response_time` is already there) and skip header reading.

3. **Example market ticker validity**
   - What we know: The hardcoded example needs a real market ticker and timestamp that exists in the database.
   - What's unclear: Which specific ticker/timestamp combination will reliably work in dev and production.
   - Recommendation: Use a well-known historical market ticker. The exact value can be determined during implementation by querying the markets endpoint. Use a ticker + timestamp that's guaranteed to have data.

## Sidebar Navigation Update

The sidebar must be updated to add the Playground item in the correct position (after Overview, before API Keys). The relevant file is:

**File:** `/Users/samuelclark/Desktop/kalshibook/dashboard/src/components/sidebar/app-sidebar.tsx`

Current nav order: Overview, API Keys, Billing, Documentation
New nav order: Overview, **Playground**, API Keys, Billing, Documentation

Icon recommendation: `Terminal` from lucide-react (represents command-line/shell interaction, matches the curl-first approach).

## Sources

### Primary (HIGH confidence)
- KalshiBook codebase direct inspection -- dashboard structure, API patterns, component library, existing auth flows, backend endpoint definitions
- Next.js official docs (nextjs.org/docs) -- Route Handlers, rewrites, proxy patterns
- shadcn/ui docs (ui.shadcn.com) -- Tabs, Select, Tooltip, Collapsible components
- prism-react-renderer GitHub (github.com/FormidableLabs/prism-react-renderer) -- v2 API, themes, language support

### Secondary (MEDIUM confidence)
- Frontend engineering blog comparison of React syntax highlighting libraries (frontendeng.dev) -- verified prism-react-renderer as well-maintained choice
- Multiple Next.js proxy implementation guides -- confirmed rewrites approach is correct and sufficient

### Tertiary (LOW confidence)
- prism-react-renderer default language bundle list -- could not confirm bash inclusion definitively; needs implementation-time verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are already installed or well-established; only one new dependency (prism-react-renderer)
- Architecture: HIGH -- follows existing dashboard patterns exactly; split-panel layout is standard React
- Pitfalls: HIGH -- identified from direct codebase inspection and known CORS/auth patterns
- Discretion areas: MEDIUM -- recommendations based on codebase patterns and Tavily reference, but user may have different preferences

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (stable domain, no rapidly changing dependencies)
