"use client";

// ---------------------------------------------------------------------------
// OrderbookPreview -- side-by-side yes/no orderbook table for Preview tab
// ---------------------------------------------------------------------------

export interface OrderbookLevel {
  price: number;
  quantity: number;
}

export interface OrderbookData {
  yes: OrderbookLevel[];
  no: OrderbookLevel[];
  market_ticker?: string;
  ts?: number;
  snapshot_basis?: string;
  deltas_applied?: number;
}

export function isOrderbookData(data: unknown): data is OrderbookData {
  if (typeof data !== "object" || data === null) return false;
  const obj = data as Record<string, unknown>;
  return Array.isArray(obj.yes) && Array.isArray(obj.no);
}

interface OrderbookPreviewProps {
  data: unknown;
}

function LevelTable({
  side,
  levels,
  color,
}: {
  side: string;
  levels: OrderbookLevel[];
  color: string;
}) {
  return (
    <div>
      <h4 className={`text-sm font-semibold mb-2 ${color}`}>{side}</h4>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-muted-foreground">
            <th className="text-left py-1.5 px-2 font-medium">Price</th>
            <th className="text-right py-1.5 px-2 font-medium">Qty</th>
          </tr>
        </thead>
        <tbody>
          {levels.length === 0 ? (
            <tr>
              <td
                colSpan={2}
                className="py-2 px-2 text-center text-muted-foreground"
              >
                No levels
              </td>
            </tr>
          ) : (
            levels.map((level, i) => (
              <tr key={i} className="border-b last:border-b-0">
                <td className="py-1.5 px-2">{level.price}&cent;</td>
                <td className="py-1.5 px-2 text-right tabular-nums">
                  {level.quantity}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function OrderbookPreview({ data }: OrderbookPreviewProps) {
  if (!isOrderbookData(data)) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Preview not available for this response format
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {/* Summary header */}
      {(data.market_ticker || data.ts || data.snapshot_basis) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground border-b pb-2">
          {data.market_ticker && <span>Ticker: {data.market_ticker}</span>}
          {data.ts && (
            <span>
              Timestamp: {new Date(data.ts * 1000).toISOString()}
            </span>
          )}
          {data.snapshot_basis && (
            <span>Basis: {data.snapshot_basis}</span>
          )}
          {typeof data.deltas_applied === "number" && (
            <span>Deltas: {data.deltas_applied}</span>
          )}
        </div>
      )}

      {/* Side-by-side tables */}
      <div className="grid grid-cols-2 gap-4">
        <LevelTable side="Yes" levels={data.yes} color="text-green-600" />
        <LevelTable side="No" levels={data.no} color="text-red-600" />
      </div>
    </div>
  );
}
