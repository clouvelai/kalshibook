"use client";

import { useRef, useEffect, useCallback } from "react";
import type { OrderbookLevel } from "@/components/playground/orderbook-preview";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DepthChartProps {
  yes: OrderbookLevel[];
  no: OrderbookLevel[];
  className?: string;
}

interface DepthPoint {
  price: number;
  cumulative: number;
}

// ---------------------------------------------------------------------------
// Data transformation (pure functions)
// ---------------------------------------------------------------------------

function cumulativeYes(levels: OrderbookLevel[]): DepthPoint[] {
  if (levels.length === 0) return [];
  const sorted = [...levels].sort((a, b) => b.price - a.price);
  let sum = 0;
  return sorted.map((l) => ({ price: l.price, cumulative: (sum += l.quantity) }));
}

function cumulativeNo(levels: OrderbookLevel[]): DepthPoint[] {
  if (levels.length === 0) return [];
  const sorted = [...levels].sort((a, b) => a.price - b.price);
  let sum = 0;
  return sorted.map((l) => ({ price: l.price, cumulative: (sum += l.quantity) }));
}

// ---------------------------------------------------------------------------
// Drawing constants
// ---------------------------------------------------------------------------

const PADDING = { top: 20, right: 20, bottom: 40, left: 60 };

const YES_STROKE = "rgba(34, 197, 94, 0.8)";
const YES_FILL = "rgba(34, 197, 94, 0.15)";
const NO_STROKE = "rgba(239, 68, 68, 0.8)";
const NO_FILL = "rgba(239, 68, 68, 0.15)";

const GRID_COLOR = "rgba(128, 128, 128, 0.15)";
const LABEL_COLOR = "rgba(128, 128, 128, 0.7)";
const LABEL_FONT = "12px system-ui, -apple-system, sans-serif";
const EMPTY_FONT = "14px system-ui, -apple-system, sans-serif";

// ---------------------------------------------------------------------------
// Drawing functions
// ---------------------------------------------------------------------------

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

function drawGrid(
  ctx: CanvasRenderingContext2D,
  chartW: number,
  chartH: number,
  maxQty: number,
) {
  ctx.save();

  // X-axis gridlines and labels (price ticks: 0, 25, 50, 75, 100)
  const priceTicks = [0, 25, 50, 75, 100];
  ctx.font = LABEL_FONT;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";

  for (const price of priceTicks) {
    const x = PADDING.left + (price / 100) * chartW;

    // Gridline
    ctx.strokeStyle = GRID_COLOR;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, PADDING.top);
    ctx.lineTo(x, PADDING.top + chartH);
    ctx.stroke();

    // Label
    ctx.fillStyle = LABEL_COLOR;
    ctx.fillText(`${price}`, x, PADDING.top + chartH + 6);
  }

  // X-axis title
  ctx.fillStyle = LABEL_COLOR;
  ctx.textBaseline = "bottom";
  ctx.fillText(
    "Price (cents)",
    PADDING.left + chartW / 2,
    PADDING.top + chartH + PADDING.bottom - 2,
  );

  // Y-axis gridlines and labels (~4 evenly spaced quantity ticks)
  const yTickCount = 4;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  for (let i = 0; i <= yTickCount; i++) {
    const qty = (maxQty * i) / yTickCount;
    const y = PADDING.top + chartH - (qty / maxQty) * chartH;

    // Gridline (skip baseline)
    if (i > 0) {
      ctx.strokeStyle = GRID_COLOR;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(PADDING.left, y);
      ctx.lineTo(PADDING.left + chartW, y);
      ctx.stroke();
    }

    // Label
    ctx.fillStyle = LABEL_COLOR;
    const label = qty >= 1000 ? `${(qty / 1000).toFixed(1)}k` : Math.round(qty).toString();
    ctx.fillText(label, PADDING.left - 8, y);
  }

  // Y-axis title (rotated)
  ctx.save();
  ctx.translate(14, PADDING.top + chartH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = LABEL_COLOR;
  ctx.fillText("Cumulative Qty", 0, 0);
  ctx.restore();

  // Axes lines
  ctx.strokeStyle = GRID_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath();
  // X-axis
  ctx.moveTo(PADDING.left, PADDING.top + chartH);
  ctx.lineTo(PADDING.left + chartW, PADDING.top + chartH);
  // Y-axis
  ctx.moveTo(PADDING.left, PADDING.top);
  ctx.lineTo(PADDING.left, PADDING.top + chartH);
  ctx.stroke();

  ctx.restore();
}

function drawLegend(ctx: CanvasRenderingContext2D, width: number) {
  const legendX = width - PADDING.right - 100;
  const legendY = PADDING.top + 8;
  const boxSize = 12;
  const spacing = 20;

  ctx.font = LABEL_FONT;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";

  // Yes legend
  ctx.fillStyle = YES_STROKE;
  ctx.fillRect(legendX, legendY, boxSize, boxSize);
  ctx.fillStyle = LABEL_COLOR;
  ctx.fillText("Yes", legendX + boxSize + 4, legendY + boxSize / 2);

  // No legend
  ctx.fillStyle = NO_STROKE;
  ctx.fillRect(legendX, legendY + spacing, boxSize, boxSize);
  ctx.fillStyle = LABEL_COLOR;
  ctx.fillText("No", legendX + boxSize + 4, legendY + spacing + boxSize / 2);
}

function drawEmptyState(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.clearRect(0, 0, w, h);
  ctx.font = EMPTY_FONT;
  ctx.fillStyle = LABEL_COLOR;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("No depth data", w / 2, h / 2);
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

  // Empty state
  if (yesCurve.length === 0 && noCurve.length === 0) {
    drawEmptyState(ctx, w, h);
    return;
  }

  const maxQty = Math.max(
    ...yesCurve.map((p) => p.cumulative),
    ...noCurve.map((p) => p.cumulative),
    1,
  );

  const scaleX = (price: number) => PADDING.left + (price / 100) * chartW;
  const scaleY = (qty: number) => PADDING.top + chartH - (qty / maxQty) * chartH;

  // Clear
  ctx.clearRect(0, 0, w, h);

  // Grid and axes
  drawGrid(ctx, chartW, chartH, maxQty);

  // Data series
  drawSteppedArea(ctx, yesCurve, scaleX, scaleY, baseline, YES_STROKE, YES_FILL);
  drawSteppedArea(ctx, noCurve, scaleX, scaleY, baseline, NO_STROKE, NO_FILL);

  // Legend
  drawLegend(ctx, w);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DepthChart({ yes, no, className }: DepthChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const redraw = useCallback(() => {
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

    // Draw using logical dimensions
    draw(ctx, yes, no, rect.width, rect.height);
  }, [yes, no]);

  // Draw on data change
  useEffect(() => {
    redraw();
  }, [redraw]);

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
