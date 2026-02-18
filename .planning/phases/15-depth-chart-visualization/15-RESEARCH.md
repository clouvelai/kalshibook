# Phase 15: Depth Chart Visualization - Research

**Researched:** 2026-02-18
**Domain:** HTML Canvas 2D rendering, orderbook depth chart visualization, React canvas component patterns
**Confidence:** HIGH

## Summary

Phase 15 adds a visual depth chart to the existing playground, showing cumulative orderbook depth for Yes and No sides across the 0-100 cent price range. The depth chart renders on an HTML `<canvas>` element (required: DPTH-02) and appears as a new tab alongside the existing JSON and Preview sub-tabs in the response panel (DPTH-03). No new backend endpoints are needed -- the existing orderbook response data (`yes[]` and `no[]` arrays of `{price, quantity}` pairs) already contains everything required to compute and render cumulative depth curves.

The core technical work is a single React component (`DepthChart`) that takes orderbook data, transforms it into cumulative depth series, and draws stepped area fills on a Canvas 2D context. The component must handle high-DPI rendering (devicePixelRatio scaling), responsive resizing (ResizeObserver), and provide accessible fallback content. The drawing logic is pure functions that operate on a canvas context -- no charting library is needed for this use case since the visualization is a simple stepped area chart with two filled regions.

The main architectural decision is where the depth chart tab lives. The existing response panel (`ResponsePanel`) already has `JSON | Preview` sub-tabs inside a Tabs component. Adding a `Depth` tab there is the natural location. The depth chart should only be enabled when the response data is recognized as orderbook data (using the existing `isOrderbookData` type guard from `orderbook-preview.tsx`). For non-orderbook responses, the tab can be hidden or disabled.

**Primary recommendation:** Build a pure Canvas 2D depth chart component (~150-200 lines) with no external charting library. Wire it as a third sub-tab ("Depth") in the existing ResponsePanel alongside JSON and Preview. Transform orderbook `{price, quantity}[]` data into cumulative depth series using a simple accumulation function. Handle high-DPI and responsive sizing via devicePixelRatio + ResizeObserver. No backend changes needed.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React (useRef, useEffect, useCallback) | 19.1.0 | Canvas ref management, draw lifecycle, resize handling | Already in use |
| HTML Canvas 2D API | Browser native | Depth chart rendering surface | Required by DPTH-02; no library dependency |
| ResizeObserver API | Browser native | Responsive canvas resizing when container changes | Built-in, no npm dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | - | - | No additional libraries needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw Canvas 2D | Chart.js / react-chartjs-2 | Chart.js adds ~60KB gzipped and requires learning its config API for a single chart type. Raw Canvas is ~150 lines for this stepped area chart, zero bundle impact, and full control for future animation (v1.3). |
| Raw Canvas 2D | Lightweight-charts (TradingView) | Purpose-built for financial charts but is ~130KB and opinionated about axis/crosshair behavior. Overkill for a static depth chart. Worth revisiting if Phase 15+ adds time-series or candlestick charts. |
| Raw Canvas 2D | D3 + Canvas | D3 is powerful but the SVG-first mental model fights Canvas rendering. d3-scale is the only useful piece, and for a 0-100 fixed range, manual scale math is trivial. |
| ResizeObserver (native) | use-resize-observer npm package | The npm package adds convenience but introduces a dependency for 10 lines of code. Native ResizeObserver is supported in all modern browsers. |

**Installation:**
```bash
# No new packages needed -- this phase is entirely built on existing dependencies
```

## Architecture Patterns

### Recommended Project Structure

**Frontend (new + modified):**
```
dashboard/src/
  components/
    playground/
      depth-chart.tsx          # NEW: Canvas-based depth chart component
      response-panel.tsx       # MODIFIED: add "Depth" sub-tab alongside JSON and Preview
```

Two files total. One new component, one modification to an existing file.

### Pattern 1: React Canvas Component with useRef + useEffect
**What:** A React component that renders a `<canvas>` element, uses `useRef` for the canvas reference, and `useEffect` for drawing whenever data changes.
**When to use:** Any Canvas 2D rendering in React.
**Example:**
```typescript
// Source: verified pattern from React docs + web.dev High DPI Canvas article
interface DepthChartProps {
  data: OrderbookData;
  className?: string;
}

export function DepthChart({ data, className }: DepthChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // High-DPI setup
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.scale(dpr, dpr);

    // Draw depth chart using rect.width and rect.height as logical dimensions
    drawDepthChart(ctx, data, rect.width, rect.height);
  }, [data]);

  return (
    <div ref={containerRef} className={className}>
      <canvas ref={canvasRef} role="img" aria-label="Orderbook depth chart" />
    </div>
  );
}
```

### Pattern 2: Cumulative Depth Data Transformation
**What:** Transform raw orderbook levels `{price, quantity}[]` into cumulative depth series for the chart. For prediction markets, "Yes" bids show demand at each price (cumulative from highest price down), and "No" asks show supply (cumulative from lowest price up).
**When to use:** Before every draw call, whenever orderbook data changes.
**Example:**
```typescript
interface DepthPoint {
  price: number;      // 1-99 cents
  cumulative: number;  // total quantity at this price or better
}

function computeCumulativeDepth(
  levels: { price: number; quantity: number }[],
  side: "yes" | "no"
): DepthPoint[] {
  if (levels.length === 0) return [];

  // Yes side: buyers willing to pay this price or MORE
  // Sort descending by price, accumulate from top
  // Result: at price P, total quantity from all levels >= P
  if (side === "yes") {
    const sorted = [...levels].sort((a, b) => b.price - a.price);
    let cumulative = 0;
    return sorted.map((level) => {
      cumulative += level.quantity;
      return { price: level.price, cumulative };
    });
  }

  // No side: sellers willing to sell at this price or LESS
  // Sort ascending by price, accumulate from bottom
  // Result: at price P, total quantity from all levels <= P
  const sorted = [...levels].sort((a, b) => a.price - b.price);
  let cumulative = 0;
  return sorted.map((level) => {
    cumulative += level.quantity;
    return { price: level.price, cumulative };
  });
}
```

### Pattern 3: Stepped Area Fill on Canvas
**What:** Draw the depth chart as two filled stepped areas -- green for Yes (bids), red for No (asks) -- with semi-transparent fills.
**When to use:** The core drawing routine called from useEffect.
**Example:**
```typescript
function drawDepthChart(
  ctx: CanvasRenderingContext2D,
  data: OrderbookData,
  width: number,
  height: number
) {
  const PADDING = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartW = width - PADDING.left - PADDING.right;
  const chartH = height - PADDING.top - PADDING.bottom;

  // Compute cumulative series
  const yesCurve = computeCumulativeDepth(data.yes, "yes");
  const noCurve = computeCumulativeDepth(data.no, "no");

  // Find max cumulative for Y-axis scale
  const maxQty = Math.max(
    ...yesCurve.map((p) => p.cumulative),
    ...noCurve.map((p) => p.cumulative),
    1 // avoid division by zero
  );

  // Scale functions
  const scaleX = (price: number) =>
    PADDING.left + (price / 100) * chartW;
  const scaleY = (qty: number) =>
    PADDING.top + chartH - (qty / maxQty) * chartH;

  // Clear
  ctx.clearRect(0, 0, width, height);

  // Draw Yes (bid) side -- green stepped area
  drawSteppedArea(ctx, yesCurve, scaleX, scaleY, chartH + PADDING.top,
    "rgba(34, 197, 94, 0.8)",   // stroke
    "rgba(34, 197, 94, 0.15)"   // fill
  );

  // Draw No (ask) side -- red stepped area
  drawSteppedArea(ctx, noCurve, scaleX, scaleY, chartH + PADDING.top,
    "rgba(239, 68, 68, 0.8)",   // stroke
    "rgba(239, 68, 68, 0.15)"   // fill
  );

  // Draw axes, labels, gridlines
  drawAxes(ctx, PADDING, chartW, chartH, maxQty);
}
```

### Pattern 4: ResizeObserver for Responsive Canvas
**What:** Use ResizeObserver to detect when the container div resizes (due to window resize, sidebar toggle, etc.) and redraw the canvas at the new size.
**When to use:** Any canvas-based component that should be responsive.
**Example:**
```typescript
useEffect(() => {
  const container = containerRef.current;
  if (!container) return;

  const observer = new ResizeObserver(() => {
    // Trigger redraw (set state or call draw directly)
    requestAnimationFrame(() => draw());
  });

  observer.observe(container);
  return () => observer.disconnect();
}, [draw]); // draw is a stable useCallback
```

### Pattern 5: Depth Tab Integration into ResponsePanel
**What:** Add "Depth" as a third sub-tab in the existing ResponsePanel, alongside "JSON" and "Preview". Show it only when data is orderbook-shaped.
**When to use:** This is the integration point (DPTH-03 / PLAY-05).
**Example:**
```tsx
// In response-panel.tsx
import { DepthChart } from "@/components/playground/depth-chart";

// Inside the component, after existing JSON and Preview tabs:
const showDepth = isOrderbookData(data);

<Tabs defaultValue="json" className="w-full">
  <div className="px-4 pt-3">
    <TabsList>
      <TabsTrigger value="json">JSON</TabsTrigger>
      <TabsTrigger value="preview">Preview</TabsTrigger>
      {showDepth && <TabsTrigger value="depth">Depth</TabsTrigger>}
    </TabsList>
  </div>

  {/* ... existing JSON and Preview TabsContent ... */}

  {showDepth && (
    <TabsContent value="depth" className="px-4 pb-4 pt-2">
      <DepthChart data={data as OrderbookData} className="h-[400px]" />
    </TabsContent>
  )}
</Tabs>
```

### Anti-Patterns to Avoid
- **Using SVG for the depth chart:** The requirement explicitly mandates Canvas (DPTH-02) for future animation support. SVG-to-Canvas rewrites are painful because the rendering model is fundamentally different (retained vs immediate mode).
- **Installing a charting library for a single chart type:** Chart.js, Recharts, or Highcharts add significant bundle size (40-130KB gzipped) for what amounts to two filled stepped lines on a known 0-100 axis. The custom Canvas code is ~150 lines and gives full control.
- **Drawing directly in the component body:** Canvas drawing is a side effect and must happen inside useEffect, not during render. Drawing during render causes double-draws in StrictMode and breaks the React lifecycle.
- **Forgetting devicePixelRatio scaling:** Without DPI scaling, the chart will look blurry on Retina/HiDPI displays (MacBooks, modern phones). This is a very common Canvas mistake.
- **Using setInterval for resize handling:** ResizeObserver is the correct API for detecting container size changes. Window resize events miss many cases (sidebar toggles, layout changes).
- **Mutating props data during cumulative calculation:** Always spread/copy the levels array before sorting (`[...levels].sort(...)`) to avoid mutating the React state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| High-DPI canvas setup | Manual pixel calculations | Standard `dpr * rect.width/height` + `ctx.scale(dpr, dpr)` pattern | Well-documented 5-line pattern from web.dev, easy to get wrong if improvised |
| Responsive canvas sizing | window.onresize listener | ResizeObserver on container div | Catches all resize causes (window, sidebar, layout shifts), not just window resize |
| Orderbook type detection | New type guard | Reuse existing `isOrderbookData()` from `orderbook-preview.tsx` | Already proven, checks for yes/no arrays -- extract to shared location or import directly |

**Key insight:** The depth chart visualization is simple enough that no external library is warranted. The fixed 0-100 cent price range eliminates dynamic axis scaling complexity. The stepped area fill is a basic Canvas path operation. The main complexity is in the boilerplate (DPI, resize, cleanup) rather than the chart logic itself.

## Common Pitfalls

### Pitfall 1: Blurry Canvas on Retina Displays
**What goes wrong:** The depth chart renders at 1x resolution, looking noticeably fuzzy on MacBooks and high-DPI monitors.
**Why it happens:** Canvas pixel buffer defaults to CSS pixel dimensions. On a 2x display, this renders at half the native resolution.
**How to avoid:** Always multiply canvas.width and canvas.height by `window.devicePixelRatio`, then call `ctx.scale(dpr, dpr)`. Set CSS dimensions via `style.width` and `style.height` to the original (logical) values.
**Warning signs:** Text and lines look blurry; thin lines appear anti-aliased when they should be crisp.

### Pitfall 2: Canvas Not Resizing with Container
**What goes wrong:** The depth chart renders at initial size but does not adapt when the browser window or container panel resizes.
**Why it happens:** Canvas dimensions are set once on mount but never updated. Canvas does not auto-resize like block-level elements.
**How to avoid:** Use ResizeObserver on the container div. On each resize callback, recalculate canvas dimensions and redraw. Disconnect the observer in the useEffect cleanup function.
**Warning signs:** Chart appears stretched, cropped, or tiny after window resize.

### Pitfall 3: Cumulative Direction Confusion for Prediction Markets
**What goes wrong:** The depth curves are calculated in the wrong direction, showing inverted depth (e.g., bids accumulate upward from low prices instead of downward from high prices).
**Why it happens:** Traditional stock market depth charts have bids accumulating from mid-price outward to the left (decreasing price). Prediction market orderbooks (0-100 cents) need different treatment: Yes bids represent "willing to pay X cents or more for YES outcome", so cumulative starts from the highest price.
**How to avoid:** For Yes side: sort descending by price, accumulate top-to-bottom. For No side: sort ascending by price, accumulate bottom-to-top. The visual result should show Yes depth rising from right-to-left (high prices have more cumulative interest) and No depth rising from left-to-right.
**Warning signs:** The depth curves cross unexpectedly or the "deeper" end is on the wrong side.

### Pitfall 4: Empty or Single-Level Orderbooks
**What goes wrong:** The chart crashes or renders nothing when an orderbook has 0 or 1 levels on one side.
**Why it happens:** Edge case not handled in cumulative calculation or max quantity computation.
**How to avoid:** Guard against empty arrays at the start of computeCumulativeDepth (return []). Use `Math.max(...values, 1)` to prevent division by zero in Y-axis scaling. Show a "No depth data" message when both sides are empty.
**Warning signs:** White canvas with no error, or NaN in axis labels.

### Pitfall 5: Memory Leak from ResizeObserver
**What goes wrong:** ResizeObserver continues firing after the component unmounts, causing state updates on unmounted components.
**Why it happens:** Missing cleanup in useEffect return function.
**How to avoid:** Always call `observer.disconnect()` in the useEffect cleanup. If using requestAnimationFrame for debouncing, also call `cancelAnimationFrame` in cleanup.
**Warning signs:** React warnings about "Can't perform a state update on an unmounted component" in the console.

### Pitfall 6: React StrictMode Double-Mount Canvas Issue
**What goes wrong:** In development, the depth chart draws twice or flickers on mount.
**Why it happens:** React 18+ StrictMode deliberately double-invokes effects to expose cleanup bugs. The first mount draws, the cleanup clears, and the second mount draws again.
**How to avoid:** This is development-only behavior and is correct. Ensure the useEffect cleanup calls `ctx.clearRect(0, 0, canvas.width, canvas.height)` or simply let the redraw overwrite. No production impact.
**Warning signs:** Brief flash on mount in dev mode only.

## Code Examples

### Complete DepthChart Component Skeleton
```typescript
// Source: assembled from web.dev canvas-hidipi + MDN ResizeObserver + codebase patterns
"use client";

import { useRef, useEffect, useCallback } from "react";

interface OrderbookLevel {
  price: number;
  quantity: number;
}

interface DepthChartProps {
  yes: OrderbookLevel[];
  no: OrderbookLevel[];
  className?: string;
}

interface DepthPoint {
  price: number;
  cumulative: number;
}

// --- Data transformation ---

function cumulativeYes(levels: OrderbookLevel[]): DepthPoint[] {
  const sorted = [...levels].sort((a, b) => b.price - a.price);
  let sum = 0;
  return sorted.map((l) => ({ price: l.price, cumulative: (sum += l.quantity) }));
}

function cumulativeNo(levels: OrderbookLevel[]): DepthPoint[] {
  const sorted = [...levels].sort((a, b) => a.price - b.price);
  let sum = 0;
  return sorted.map((l) => ({ price: l.price, cumulative: (sum += l.quantity) }));
}

// --- Drawing ---

const PADDING = { top: 20, right: 20, bottom: 40, left: 60 };
const YES_STROKE = "rgba(34, 197, 94, 0.8)";
const YES_FILL = "rgba(34, 197, 94, 0.15)";
const NO_STROKE = "rgba(239, 68, 68, 0.8)";
const NO_FILL = "rgba(239, 68, 68, 0.15)";

function drawSteppedArea(
  ctx: CanvasRenderingContext2D,
  points: DepthPoint[],
  scaleX: (p: number) => number,
  scaleY: (q: number) => number,
  baseline: number,
  stroke: string,
  fill: string,
) {
  if (points.length === 0) return;

  ctx.beginPath();
  ctx.moveTo(scaleX(points[0].price), baseline);

  for (let i = 0; i < points.length; i++) {
    const x = scaleX(points[i].price);
    const y = scaleY(points[i].cumulative);
    ctx.lineTo(x, y);
    if (i < points.length - 1) {
      ctx.lineTo(scaleX(points[i + 1].price), y); // horizontal step
    }
  }

  // Close path back to baseline for fill
  const lastX = scaleX(points[points.length - 1].price);
  ctx.lineTo(lastX, baseline);
  ctx.closePath();

  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2;
  ctx.stroke();
}

function draw(
  ctx: CanvasRenderingContext2D,
  yes: OrderbookLevel[],
  no: OrderbookLevel[],
  w: number,
  h: number,
) {
  const chartW = w - PADDING.left - PADDING.right;
  const chartH = h - PADDING.top - PADDING.bottom;
  const baseline = PADDING.top + chartH;

  const yesCurve = cumulativeYes(yes);
  const noCurve = cumulativeNo(no);

  const maxQty = Math.max(
    ...yesCurve.map((p) => p.cumulative),
    ...noCurve.map((p) => p.cumulative),
    1,
  );

  const scaleX = (price: number) => PADDING.left + (price / 100) * chartW;
  const scaleY = (qty: number) => PADDING.top + chartH - (qty / maxQty) * chartH;

  ctx.clearRect(0, 0, w, h);

  // Grid and axes
  drawGrid(ctx, PADDING, chartW, chartH, maxQty);

  // Data series
  drawSteppedArea(ctx, yesCurve, scaleX, scaleY, baseline, YES_STROKE, YES_FILL);
  drawSteppedArea(ctx, noCurve, scaleX, scaleY, baseline, NO_STROKE, NO_FILL);

  // Legend
  drawLegend(ctx, w);
}

// --- Component ---

export function DepthChart({ yes, no, className }: DepthChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.scale(dpr, dpr);

    draw(ctx, yes, no, rect.width, rect.height);
  }, [yes, no]);

  // Draw on data change
  useEffect(() => { redraw(); }, [redraw]);

  // Resize handling
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      requestAnimationFrame(redraw);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [redraw]);

  return (
    <div ref={containerRef} className={className}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={`Depth chart: ${yes.length} Yes levels, ${no.length} No levels`}
      >
        Orderbook depth visualization showing cumulative Yes and No quantities
        across the 0-100 cent price range.
      </canvas>
    </div>
  );
}
```

### ResponsePanel Tab Integration
```tsx
// Source: existing response-panel.tsx pattern
// Add "Depth" tab alongside existing "JSON" and "Preview"

import { DepthChart } from "@/components/playground/depth-chart";

// Inside ResponsePanel component:
const showDepth = isOrderbookData(data);

<Tabs defaultValue="json" className="w-full">
  <div className="px-4 pt-3">
    <TabsList>
      <TabsTrigger value="json">JSON</TabsTrigger>
      <TabsTrigger value="preview">Preview</TabsTrigger>
      {showDepth && <TabsTrigger value="depth">Depth</TabsTrigger>}
    </TabsList>
  </div>

  <TabsContent value="json" className="px-4 pb-4 pt-2">
    <CodeBlock code={JSON.stringify(data, null, 2)} language="json" />
  </TabsContent>

  <TabsContent value="preview" className="pb-4">
    <OrderbookPreview data={data} />
  </TabsContent>

  {showDepth && (
    <TabsContent value="depth" className="px-4 pb-4 pt-2">
      <DepthChart
        yes={(data as OrderbookData).yes}
        no={(data as OrderbookData).no}
        className="h-[400px] w-full"
      />
    </TabsContent>
  )}
</Tabs>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SVG for all charts | Canvas for performance-critical/animated charts | Gradual shift since 2020-2022 | Canvas handles 60fps updates; SVG better for small static charts |
| Chart.js for everything | Right-size the tool: Chart.js for complex multi-chart dashboards, raw Canvas for single simple charts | 2024+ | Bundle size awareness; Tree-shaking doesn't help when you only need one chart type |
| window.onresize for canvas | ResizeObserver on container | 2020+ (browser support universal by 2022) | Catches all resize sources, not just window; cleaner API |
| Canvas 1x rendering | devicePixelRatio scaling mandatory | Always true but enforcement increased with 2x+ becoming standard | Blurry canvas is unacceptable on modern displays |

**Deprecated/outdated:**
- `backingStorePixelRatio`: Old Canvas property used to detect non-standard DPI on some browsers. No longer needed -- `window.devicePixelRatio` is universal.
- `CanvasRenderingContext2D.webkitBackingStorePixelRatio`: Safari-only historical API. Not needed since Safari 8+.

## Open Questions

1. **Should the depth chart tab auto-select when orderbook data arrives?**
   - What we know: Currently the response panel defaults to "json" tab. After executing an orderbook request, the user must manually click "Depth" to see the visualization.
   - What's unclear: Whether auto-switching to the depth tab would be a better UX for orderbook responses.
   - Recommendation: Keep "json" as the default tab (consistent behavior). The "Depth" tab appears only for orderbook data, drawing the user's eye naturally. Auto-switching tabs can be disorienting. Revisit if user feedback indicates otherwise.

2. **Should the isOrderbookData type guard be extracted to a shared utility?**
   - What we know: The `isOrderbookData` function is currently defined locally in `orderbook-preview.tsx`. The depth chart component also needs it (or needs the same check).
   - What's unclear: Whether to extract it to a shared location or duplicate the simple check.
   - Recommendation: Extract the `isOrderbookData` type guard and the `OrderbookData`/`OrderbookLevel` interfaces to a shared file (e.g., `lib/orderbook-types.ts` or at the top of a shared types file). Both `orderbook-preview.tsx` and `response-panel.tsx` import from there. This prevents duplication and ensures consistent type checking.

3. **Dark mode canvas colors?**
   - What we know: The dashboard uses `next-themes` for dark mode. Canvas drawing uses explicit RGB colors, not CSS variables.
   - What's unclear: Whether the depth chart colors should adapt to dark/light mode.
   - Recommendation: Use semi-transparent fills that work on both light and dark backgrounds: green with alpha 0.15 fill and 0.8 stroke, red with alpha 0.15 fill and 0.8 stroke. For text (axis labels, gridlines), detect the current theme and use appropriate foreground colors, OR read the CSS custom property `--foreground` from the computed style of the container. Alternatively, use a dark background (like the existing CodeBlock uses `#1e1e1e`) to avoid theme-sensitivity entirely.

4. **Hover/tooltip interaction on the depth chart?**
   - What we know: The requirement says "static depth chart" (animation deferred to v1.3). But basic hover showing price/quantity at cursor position is a common depth chart feature.
   - What's unclear: Whether basic hover is in scope for Phase 15 or deferred.
   - Recommendation: Defer hover/tooltip to a future phase. The static chart satisfies all four requirements (DPTH-01, DPTH-02, DPTH-03, PLAY-05). Adding mouse interaction increases complexity significantly (mousemove handler, coordinate calculation, redraw loop, tooltip positioning). Ship static first, add interactivity later.

## Depth Chart Data Flow

For clarity, here is the complete data flow from backend to rendered chart:

```
Backend: reconstruct_orderbook()
  -> returns { yes: [{price: 95, quantity: 50}, ...], no: [{price: 5, quantity: 30}, ...], ... }

Frontend: playground demo or API call
  -> PlaygroundResult.data contains the orderbook object

ResponsePanel: isOrderbookData(data) check
  -> if true, show "Depth" tab

DepthChart component:
  -> receives yes[] and no[] as props
  -> cumulativeYes(): sort desc by price, accumulate → [{price: 95, cum: 50}, {price: 90, cum: 120}, ...]
  -> cumulativeNo(): sort asc by price, accumulate → [{price: 5, cum: 30}, {price: 10, cum: 75}, ...]
  -> Canvas draw: stepped area fills from cumulative data
```

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `dashboard/src/components/playground/response-panel.tsx` -- existing JSON/Preview tab structure, isOrderbookData type guard pattern
- Codebase inspection: `dashboard/src/components/playground/orderbook-preview.tsx` -- OrderbookData interface, isOrderbookData function, existing table-based preview
- Codebase inspection: `src/api/services/reconstruction.py` -- orderbook data shape returned by backend ({yes, no} arrays of {price, quantity})
- Codebase inspection: `dashboard/src/components/playground/code-panel.tsx` -- outer Response/Code tab structure, how ResponsePanel is integrated
- Codebase inspection: `dashboard/src/components/ui/tabs.tsx` -- shadcn Tabs component API (Tabs, TabsList, TabsTrigger, TabsContent)
- Codebase inspection: `dashboard/package.json` -- React 19.1.0, no existing canvas/charting libraries
- [web.dev: High DPI Canvas](https://web.dev/articles/canvas-hidipi) -- devicePixelRatio setup pattern
- [MDN: ResizeObserver](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver) -- responsive canvas resize handling

### Secondary (MEDIUM confidence)
- [Highcharts: Depth Chart Tutorial](https://www.highcharts.com/blog/tutorials/depth-chart-a-visual-guide-to-market-liquidity-and-order-flow/) -- cumulative depth chart data structure (price, cumulative_volume pairs), stepped area rendering with fillOpacity 0.2
- [Chart.js: Accessibility](https://www.chartjs.org/docs/latest/general/accessibility.html) -- canvas accessibility patterns (role="img", aria-label, fallback content)
- [Creating Canvas Components in React](https://www.turing.com/kb/canvas-components-in-react) -- useRef + useEffect pattern for canvas in React

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed; Canvas 2D is a browser native API; all React patterns verified against existing codebase conventions
- Architecture: HIGH -- the tab integration point is clearly defined (ResponsePanel sub-tabs); the data shape is known from codebase inspection; the component boundary is clean (one new file, one modification)
- Pitfalls: HIGH -- all pitfalls derive from well-documented Canvas gotchas (DPI, resize, cleanup) and prediction market-specific depth calculation verified against the orderbook data structure

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable domain, no fast-moving dependencies)
