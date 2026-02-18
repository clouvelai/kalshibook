"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { CoverageSummary } from "@/types/api";

const compactNumber = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function formatDateRange(start: string | null, end: string | null): string {
  if (!start || !end) return "No data";
  const s = new Date(start);
  const e = new Date(end);
  const sameYear = s.getFullYear() === e.getFullYear();
  const startFmt = s.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
  });
  const endFmt = e.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return `${startFmt} - ${endFmt}`;
}

interface CoverageSummaryCardsProps {
  summary: CoverageSummary;
}

const cards = [
  {
    label: "Markets Tracked",
    getValue: (s: CoverageSummary) => s.total_markets.toLocaleString(),
  },
  {
    label: "Total Snapshots",
    getValue: (s: CoverageSummary) => compactNumber.format(s.total_snapshots),
  },
  {
    label: "Total Deltas",
    getValue: (s: CoverageSummary) => compactNumber.format(s.total_deltas),
  },
  {
    label: "Date Range",
    getValue: (s: CoverageSummary) =>
      formatDateRange(s.date_range_start, s.date_range_end),
  },
];

export function CoverageSummaryCards({ summary }: CoverageSummaryCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label} className="py-4">
          <CardContent className="flex flex-col gap-1">
            <p className="text-xs font-medium text-muted-foreground">
              {card.label}
            </p>
            <p className="text-lg font-semibold tracking-tight">
              {card.getValue(summary)}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
