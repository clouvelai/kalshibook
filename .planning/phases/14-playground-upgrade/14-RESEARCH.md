# Phase 14: Playground Upgrade - Research

**Researched:** 2026-02-18
**Domain:** FastAPI dashboard-internal endpoints, Next.js autocomplete UI (shadcn Combobox), zero-credit demo architecture
**Confidence:** HIGH

## Summary

Phase 14 transforms the existing API Playground from a bare-bones form with a hardcoded (broken) example ticker into a polished exploration tool backed by real coverage data. The work spans four requirements: (1) pre-populate the ticker input from real captured markets, (2) add autocomplete/typeahead search over markets with confirmed data, (3) show example cards for common use cases (orderbook, trades, candles) that execute with one click, and (4) ensure all demo interactions cost zero credits.

The core technical challenge is the zero-credit demo system (PLAY-04). The existing playground fires real API requests through the billed path (`executePlaygroundRequest` in `playground.ts` using the user's API key with `require_credits` dependencies). Demo interactions must bypass this entirely. The cleanest approach is a new set of dashboard-internal FastAPI endpoints (e.g., `GET /playground/markets` for autocomplete, `POST /playground/demo` for zero-credit demo execution) that use JWT auth (like the coverage endpoints) instead of API key auth, avoiding the credit deduction pipeline entirely. This follows the exact pattern already established in Phase 13's coverage endpoints.

The autocomplete component requires adding `cmdk` (the shadcn Command component's dependency) and generating Popover + Command UI components via `npx shadcn add`. The existing coverage search uses a debounced input but not a dropdown autocomplete -- the playground needs a proper combobox with dropdown suggestions showing ticker, title, and coverage dates.

**Primary recommendation:** Build 2-3 new dashboard-internal FastAPI endpoints (market search for autocomplete, demo execution for zero-credit requests, and optionally a "featured examples" endpoint), consume them from the dashboard via the existing `fetchAPI` helper (JWT-authenticated), and add shadcn Combobox (Popover + Command from cmdk) for the autocomplete UI. The example cards are a frontend-only component that constructs pre-populated queries and routes them through the demo endpoint.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | New `/playground/*` dashboard-internal endpoints | Already in use, follows coverage endpoint pattern |
| asyncpg | existing | Query markets + coverage data for autocomplete and demo | Already in use for all DB access |
| Next.js | 15.5.12 | Enhanced playground page with autocomplete + example cards | Already in use |
| cmdk | ^1.0 | Headless command/combobox component (shadcn Command dependency) | Standard for shadcn combobox pattern |
| radix-ui (Popover) | 1.4.3 (installed) | Popover primitive for combobox dropdown | Already installed via radix-ui bundle |
| prism-react-renderer | 2.4.1 | Syntax highlighting for example cards' code preview | Already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn CLI | 3.8.4 (devDep) | Generate Command and Popover UI components | During implementation to scaffold combobox parts |
| lucide-react | 0.564.0 | Icons for example cards (BookOpen, BarChart, etc.) | Already installed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cmdk (shadcn Command) | Custom dropdown with Input + Popover | cmdk handles keyboard navigation, filtering, empty states -- hand-rolling duplicates solved problems |
| Dashboard-internal demo endpoints | Pre-baked static JSON responses | Static responses go stale when markets settle; live queries from coverage-confirmed markets always work |
| Single monolithic demo endpoint | Per-endpoint-type demo endpoints (orderbook, trades, candles) | Single endpoint is simpler; per-type preserves response shape parity with real endpoints |

**Installation:**
```bash
cd dashboard && npx shadcn add command popover
```
This installs `cmdk` and generates `components/ui/command.tsx` and `components/ui/popover.tsx`.

## Architecture Patterns

### Recommended Structure

**Backend (new files):**
```
src/api/routes/
  playground.py            # New: /playground/markets, /playground/demo
src/api/models.py          # Extended: PlaygroundMarketResult, DemoRequest, DemoResponse
src/api/main.py            # Modified: register playground router
```

**Frontend (modified + new):**
```
dashboard/src/
  components/
    ui/
      command.tsx           # New: shadcn Command (from cmdk)
      popover.tsx           # New: shadcn Popover
    playground/
      ticker-combobox.tsx   # New: autocomplete combobox for market ticker
      example-cards.tsx     # New: pre-populated example query cards
      use-playground.ts     # Modified: add demo mode, autocomplete state
      playground-form.tsx   # Modified: replace Input with TickerCombobox
  lib/
    api.ts                  # Extended: playground.markets(), playground.demo()
    playground.ts           # Modified: add demo execution path
  types/
    api.ts                  # Extended: PlaygroundMarket, DemoResponse types
  app/(dashboard)/
    playground/page.tsx     # Modified: add example cards section
```

### Pattern 1: Dashboard-Internal Endpoints (Zero-Credit Path)
**What:** FastAPI endpoints using `get_authenticated_user` (JWT auth) instead of `require_credits` (API key auth), matching the Phase 13 coverage endpoint pattern.
**When to use:** Any endpoint that serves dashboard UI needs without counting against user credits.
**Example:**
```python
# Source: src/api/routes/coverage.py (existing pattern)
@router.get("/playground/markets")
async def search_playground_markets(
    request: Request,
    user: dict = Depends(get_authenticated_user),  # JWT auth, NOT API key
    pool: asyncpg.Pool = Depends(get_db_pool),
    q: str = Query(default="", description="Ticker or title prefix search"),
    limit: int = Query(default=10, ge=1, le=50),
):
    # Query markets from materialized view (confirmed coverage)
    # Return ticker, title, status, coverage date range
    ...
```

### Pattern 2: Autocomplete Combobox (shadcn Popover + Command)
**What:** A searchable dropdown that queries the backend on each keystroke (debounced) and shows matching market tickers with metadata.
**When to use:** When the user needs to select from a large set of options that can't be loaded all at once.
**Example:**
```tsx
// shadcn combobox pattern (Popover + Command from cmdk)
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";

function TickerCombobox({ value, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlaygroundMarket[]>([]);

  // Debounced search against /playground/markets?q=...
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.length >= 2) {
        const data = await api.playground.markets(query);
        setResults(data);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox">{value || "Select market..."}</Button>
      </PopoverTrigger>
      <PopoverContent>
        <Command shouldFilter={false}> {/* Server-side filtering */}
          <CommandInput value={query} onValueChange={setQuery} />
          <CommandList>
            <CommandEmpty>No markets found</CommandEmpty>
            <CommandGroup>
              {results.map(m => (
                <CommandItem key={m.ticker} onSelect={() => { onSelect(m); setOpen(false); }}>
                  <span className="font-mono">{m.ticker}</span>
                  <span className="text-muted-foreground">{m.title}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

### Pattern 3: Example Cards with Pre-Populated Queries
**What:** Clickable cards that fill in the playground form with a known-good query and optionally auto-execute.
**When to use:** To give users zero-friction first experience with the API.
**Example:**
```tsx
const EXAMPLE_QUERIES = [
  {
    title: "Orderbook Reconstruction",
    description: "See the full L2 orderbook for a Bitcoin market at a specific timestamp",
    endpoint: "orderbook",
    // These get populated dynamically from /playground/markets
    params: { market_ticker: "", timestamp: "", depth: 10 },
    icon: BookOpen,
  },
  {
    title: "Trade History",
    description: "View recent trades for a prediction market",
    endpoint: "trades",
    params: { market_ticker: "", start_time: "", end_time: "", limit: 20 },
    icon: BarChart,
  },
  {
    title: "Price Candles",
    description: "Get 1-hour OHLCV candlestick data",
    endpoint: "candles",
    params: { ticker: "", start_time: "", end_time: "", interval: "1h" },
    icon: TrendingUp,
  },
];
```

### Pattern 4: Demo Execution (Zero-Credit Request)
**What:** A dashboard-internal endpoint that executes the same query logic as the billed endpoint but without credit deduction.
**When to use:** For playground demo/example card execution.
**Design choice:** Two approaches are viable:
  - **Option A (Recommended): Thin proxy endpoint.** A single `POST /playground/demo` that accepts `{ endpoint: "orderbook"|"trades"|"candles", params: {...} }` and calls the same service functions (e.g., `reconstruct_orderbook()`) but behind JWT auth instead of `require_credits`. This reuses existing business logic without duplication.
  - **Option B: Pre-baked responses.** Store example responses as static JSON. Simpler but goes stale when markets settle or data changes. Not recommended per the prior decision.

```python
@router.post("/playground/demo")
async def execute_demo(
    request: Request,
    body: DemoRequest,
    user: dict = Depends(get_authenticated_user),  # JWT only, no credits
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Execute a playground demo query without deducting credits.
    Routes to the same service functions as billed endpoints.
    """
    if body.endpoint == "orderbook":
        result = await reconstruct_orderbook(pool, body.params.market_ticker, ...)
        return DemoResponse(endpoint="orderbook", data=result, ...)
    elif body.endpoint == "trades":
        ...
```

### Anti-Patterns to Avoid
- **Reusing the billed execution path with a "free" flag:** Adding a `demo=true` parameter to existing billed endpoints creates a security surface (users could set demo=true on real requests). Keep the demo path completely separate with its own route and auth dependency.
- **Hardcoding example tickers:** The current `fillExample` function hardcodes `KXBTC-25FEB14-T96074.99` which is already broken. Examples must pull from coverage data dynamically.
- **Loading all markets client-side for autocomplete:** The markets table could grow large. Always do server-side filtering and return a limited result set.
- **Using the coverage/stats endpoint for autocomplete:** It returns event-grouped heavy payloads with segments. A dedicated lightweight endpoint returning just ticker + title + date range is much faster for typeahead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Autocomplete dropdown | Custom Input + dropdown with keyboard nav | shadcn Command (cmdk) + Popover | cmdk handles arrow keys, escape, enter, screen readers, empty states -- dozens of edge cases |
| Debounced search | Raw setTimeout management | Reuse DebouncedInput pattern from coverage-search.tsx or simple useEffect + cleanup | Already proven in codebase |
| Syntax highlighting in example cards | Custom code renderer | prism-react-renderer (already installed, used in CodeBlock) | Already working in playground |

**Key insight:** The autocomplete combobox is the most complex UI component in this phase. cmdk handles the hard parts (keyboard navigation, WAI-ARIA, focus management, filtering). Building a custom autocomplete from scratch would take 3-5x longer and miss accessibility requirements.

## Common Pitfalls

### Pitfall 1: Stale Example Data
**What goes wrong:** Hardcoded example tickers reference markets that have settled or expired, producing 404 errors on first interaction.
**Why it happens:** Markets on Kalshi settle on specific dates. A ticker valid today may not exist in a week.
**How to avoid:** Always pull example market tickers from the coverage materialized view (confirmed data exists). The `/playground/markets` endpoint should only return markets that appear in `market_coverage_stats`.
**Warning signs:** The current `fillExample()` already has this bug with `KXBTC-25FEB14-T96074.99`.

### Pitfall 2: Demo Endpoint Abused as Free API
**What goes wrong:** Users discover the demo endpoint and use it programmatically to bypass credits.
**Why it happens:** The demo endpoint runs real queries without credit deduction.
**How to avoid:** (1) Use JWT auth (session-based, not API key), making programmatic abuse harder. (2) Apply aggressive rate limiting specific to demo endpoints (e.g., 10/minute). (3) Return limited result sets (e.g., max 20 trades, depth capped at 10) so the demo is useful for exploration but not for production data extraction.
**Warning signs:** High request volume to `/playground/demo` from a single user.

### Pitfall 3: Autocomplete Query Performance
**What goes wrong:** ILIKE queries on the markets table become slow as the table grows, causing laggy typeahead.
**Why it happens:** `ILIKE '%query%'` cannot use standard B-tree indexes.
**How to avoid:** For the autocomplete endpoint, use `ILIKE 'query%'` (prefix search) which CAN use indexes, or join against the `market_coverage_stats` materialized view which is much smaller (only markets with data). Since we only want markets with confirmed coverage, querying the mat view directly (with a JOIN to markets for title) is both faster and semantically correct.
**Warning signs:** Autocomplete response time > 200ms.

### Pitfall 4: cmdk shouldFilter Misconfiguration
**What goes wrong:** The combobox double-filters results (once on server, once on client), producing confusing empty states.
**Why it happens:** cmdk's default behavior is client-side filtering. When using server-side search, you must set `shouldFilter={false}` on the `<Command>` component.
**How to avoid:** Always set `shouldFilter={false}` when the search query is sent to the server.
**Warning signs:** Typing a valid ticker that returns server results but the dropdown shows "No results."

### Pitfall 5: Example Card Timestamp Ranges
**What goes wrong:** Example cards use a timestamp that falls in a coverage gap, producing "No data available" errors.
**Why it happens:** Coverage segments have gaps. A timestamp must fall within a segment's start/end range.
**How to avoid:** The `/playground/markets` endpoint should return `segment_start` and `segment_end` for the most recent (or largest) segment. Example cards use the midpoint of that segment as the timestamp, guaranteeing data availability.
**Warning signs:** Example card "Execute" button produces an error response instead of data.

## Code Examples

### Backend: Market Search Endpoint for Autocomplete
```python
# Source: pattern from existing coverage.py
@router.get("/playground/markets")
async def search_playground_markets(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
    q: str = Query(default="", min_length=0, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT cs.market_ticker,
                   m.title,
                   m.status,
                   m.event_ticker,
                   MIN(cs.segment_start) AS first_date,
                   MAX(cs.segment_end) AS last_date
            FROM market_coverage_stats cs
            JOIN markets m ON m.ticker = cs.market_ticker
            WHERE cs.market_ticker ILIKE $1 OR m.title ILIKE $1
            GROUP BY cs.market_ticker, m.title, m.status, m.event_ticker
            ORDER BY MAX(cs.segment_end) DESC
            LIMIT $2
            """,
            f"%{q}%",
            limit,
        )
    return {
        "data": [
            {
                "ticker": row["market_ticker"],
                "title": row["title"],
                "status": row["status"],
                "event_ticker": row["event_ticker"],
                "first_date": str(row["first_date"]),
                "last_date": str(row["last_date"]),
            }
            for row in rows
        ],
        "request_id": request.state.request_id,
    }
```

### Backend: Demo Execution Endpoint
```python
@router.post("/playground/demo")
async def execute_demo(
    request: Request,
    body: DemoRequest,
    user: dict = Depends(get_authenticated_user),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Execute a demo query using the same service logic, zero credits."""
    t0 = time.monotonic()

    if body.endpoint == "orderbook":
        result = await reconstruct_orderbook(
            pool, body.market_ticker, body.timestamp, body.depth or 10
        )
        if result is None:
            raise MarketNotFoundError(body.market_ticker)
        elapsed = time.monotonic() - t0
        return {
            "endpoint": "orderbook",
            "data": result,
            "response_time": round(elapsed, 4),
            "request_id": request.state.request_id,
            "credits_cost": 0,
        }
    # ... similar for trades, candles
```

### Frontend: API Client Extensions
```typescript
// Addition to dashboard/src/lib/api.ts
playground: {
  markets: (q: string, limit = 10) =>
    fetchAPI<{ data: PlaygroundMarket[]; request_id: string }>(
      `/playground/markets?q=${encodeURIComponent(q)}&limit=${limit}`
    ),
  demo: (body: DemoRequest) =>
    fetchAPI<DemoResponse>("/playground/demo", {
      method: "POST",
      body: JSON.stringify(body),
    }),
},
```

### Frontend: Example Card Component
```tsx
function ExampleCard({ example, onExecute }: { example: ExampleQuery; onExecute: () => void }) {
  return (
    <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={onExecute}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-md bg-muted p-2">
            <example.icon className="size-5 text-muted-foreground" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-medium">{example.title}</h3>
            <p className="text-xs text-muted-foreground mt-1">{example.description}</p>
            <Badge variant="outline" className="mt-2 text-xs">
              /{example.endpoint}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded example ticker | Dynamic from coverage data | This phase | Examples always work, never go stale |
| Plain text input for ticker | Combobox with server-side autocomplete | This phase | Users discover markets they didn't know existed |
| All playground requests cost credits | Demo path with zero credits | This phase | Users explore freely before committing credits |
| Single orderbook-only playground | Multi-endpoint example cards | This phase | Users see the full API surface from day one |

**Deprecated/outdated:**
- `fillExample()` in `use-playground.ts`: Currently hardcodes a broken ticker. Will be replaced by dynamic example population from coverage data.

## Open Questions

1. **Should the demo endpoint be a single unified route or per-endpoint-type routes?**
   - What we know: A single `POST /playground/demo` with an `endpoint` discriminator field is simpler and keeps the route surface small. Per-endpoint routes (`POST /playground/demo/orderbook`, `POST /playground/demo/trades`, etc.) preserve exact response shape parity.
   - What's unclear: Whether the planner prefers fewer routes or stricter typing.
   - Recommendation: Single unified route with a discriminator. The demo response can wrap the real response shape inside a `data` field, making it easy to reuse the existing response rendering components.

2. **How many example cards and which endpoints?**
   - What we know: The three most valuable use cases are orderbook reconstruction (the flagship feature), trade history, and candles. These map to the three highest-cost endpoints (5, 2, 3 credits respectively).
   - What's unclear: Whether to also include deltas and settlements examples.
   - Recommendation: Start with 3 example cards (orderbook, trades, candles). These cover the core API surface. Deltas and settlements can be added later if needed.

3. **Should the example cards auto-execute or just fill the form?**
   - What we know: Auto-execute provides the fastest first-experience (one click to see data). Fill-only lets users inspect/modify the query first.
   - What's unclear: User preference.
   - Recommendation: Auto-execute through the demo endpoint (zero credits) with the response appearing immediately. The form fields also get populated so users can see what was queried and modify/re-run.

4. **Rate limiting on demo endpoints?**
   - What we know: The existing SlowAPI rate limiter is set to 120/min globally. Demo endpoints should be more restrictive to prevent abuse.
   - What's unclear: Exact rate limit thresholds.
   - Recommendation: Apply a per-user rate limit of 10-20 requests/minute on demo endpoints. This is generous for exploration but prevents bulk extraction.

## Endpoint-to-Credit Mapping (for reference)

| Endpoint | Method | Credit Cost | Demo Equivalent Needed |
|----------|--------|-------------|------------------------|
| `/orderbook` | POST | 5 | Yes (flagship) |
| `/trades` | POST | 2 | Yes (common use case) |
| `/candles/{ticker}` | GET | 3 | Yes (common use case) |
| `/deltas` | POST | 2 | Optional (advanced) |
| `/markets` | GET | 1 | No (low cost, not demo-worthy) |
| `/markets/{ticker}` | GET | 1 | No (low cost) |
| `/settlements` | GET | 1 | No (low cost) |
| `/events` | GET | 1 | No (low cost) |

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/api/routes/coverage.py` -- JWT auth pattern for dashboard-internal endpoints (lines 27-31)
- Codebase inspection: `src/api/deps.py` -- `get_authenticated_user` vs `require_credits` dependency patterns
- Codebase inspection: `src/api/routes/orderbook.py`, `trades.py`, `candles.py` -- service function signatures for reuse in demo endpoint
- Codebase inspection: `dashboard/src/components/playground/*` -- all 6 existing playground components analyzed
- Codebase inspection: `dashboard/src/lib/api.ts` -- JWT-authenticated `fetchAPI` helper already used by coverage
- Codebase inspection: `supabase/migrations/20260218000001_create_coverage_matview.sql` -- materialized view schema for autocomplete queries
- Codebase inspection: `dashboard/package.json` -- confirmed radix-ui 1.4.3 installed (includes Popover primitive), cmdk not yet installed
- Codebase inspection: `dashboard/components.json` -- shadcn "new-york" style, CLI version 3.8.4

### Secondary (MEDIUM confidence)
- shadcn/ui documentation: Combobox pattern uses Popover + Command (cmdk). The `shouldFilter={false}` prop is required for server-side filtering.
- cmdk library: Headless combobox with WAI-ARIA support, keyboard navigation, used by shadcn since v0.1.

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official shadcn docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries either already installed or are the standard shadcn recommendation (cmdk)
- Architecture: HIGH -- the zero-credit pattern is proven by Phase 13 coverage endpoints; the demo endpoint is a thin wrapper around existing service functions
- Pitfalls: HIGH -- the stale ticker bug is already manifesting in production code; other pitfalls derive from direct codebase analysis

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable stack, no fast-moving dependencies)
