"use client";

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type ExpandedState,
  type Row,
} from "@tanstack/react-table";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CoverageTimelineBar } from "./coverage-timeline-bar";
import { CoverageSegmentDetail } from "./coverage-segment-detail";
import type {
  EventCoverageGroup,
  MarketCoverage,
  CoverageSummary,
} from "@/types/api";

const compact = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function formatCoverageRange(
  first: string | null,
  last: string | null
): string {
  if (!first || !last) return "-";
  const s = new Date(first);
  const e = new Date(last);
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

/**
 * Each row is either an event header or a market row.
 * Event headers carry subRows (their markets).
 */
interface TableRowData {
  id: string;
  isEventHeader: boolean;
  // Event header fields
  eventTicker?: string;
  eventTitle?: string | null;
  marketCount?: number;
  // Market fields
  market?: MarketCoverage;
  // Sub rows for event groups
  subRows?: TableRowData[];
}

interface CoverageTableProps {
  events: EventCoverageGroup[];
  summary: CoverageSummary;
  onClearFilters: () => void;
}

export function CoverageTable({
  events,
  summary,
  onClearFilters,
}: CoverageTableProps) {
  const [expanded, setExpanded] = useState<ExpandedState>(true);
  const [expandedMarkets, setExpandedMarkets] = useState<
    Record<string, boolean>
  >({});

  const data = useMemo<TableRowData[]>(
    () =>
      events.map((event) => ({
        id: `event-${event.event_ticker}`,
        isEventHeader: true,
        eventTicker: event.event_ticker,
        eventTitle: event.event_title,
        marketCount: event.market_count,
        subRows: event.markets.map((m) => ({
          id: `market-${m.ticker}`,
          isEventHeader: false,
          market: m,
        })),
      })),
    [events]
  );

  const columns = useMemo<ColumnDef<TableRowData>[]>(
    () => [
      {
        id: "ticker",
        header: "Market",
        cell: ({ row }) => {
          if (row.original.isEventHeader) {
            return (
              <button
                type="button"
                onClick={row.getToggleExpandedHandler()}
                className="flex items-center gap-2 font-medium"
              >
                {row.getIsExpanded() ? (
                  <ChevronDown className="size-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="size-4 text-muted-foreground" />
                )}
                <span className="truncate">
                  {row.original.eventTitle || row.original.eventTicker}
                </span>
                <Badge variant="secondary" className="text-xs">
                  {row.original.marketCount}
                </Badge>
              </button>
            );
          }
          const m = row.original.market!;
          return (
            <div className="pl-6">
              <p className="font-mono text-sm">{m.ticker}</p>
              {m.title && (
                <p className="text-xs text-muted-foreground truncate max-w-[260px]">
                  {m.title}
                </p>
              )}
            </div>
          );
        },
      },
      {
        id: "range",
        header: "Coverage",
        cell: ({ row }) => {
          if (row.original.isEventHeader) return null;
          const m = row.original.market!;
          return (
            <span className="text-sm text-muted-foreground">
              {formatCoverageRange(m.first_date, m.last_date)}
            </span>
          );
        },
      },
      {
        id: "counts",
        header: "Data Points",
        cell: ({ row }) => {
          if (row.original.isEventHeader) return null;
          const m = row.original.market!;
          return (
            <span className="text-sm tabular-nums text-muted-foreground">
              {compact.format(m.total_snapshots)} |{" "}
              {compact.format(m.total_deltas)} |{" "}
              {compact.format(m.total_trades)}
            </span>
          );
        },
      },
      {
        id: "segments",
        header: "Segments",
        cell: ({ row }) => {
          if (row.original.isEventHeader) return null;
          const m = row.original.market!;
          return (
            <div className="flex items-center gap-2 min-w-[140px]">
              <span className="text-xs text-muted-foreground shrink-0">
                {m.segment_count}
              </span>
              {summary.date_range_start && summary.date_range_end && (
                <CoverageTimelineBar
                  segments={m.segments}
                  overallStart={summary.date_range_start}
                  overallEnd={summary.date_range_end}
                />
              )}
            </div>
          );
        },
      },
    ],
    [summary.date_range_start, summary.date_range_end]
  );

  const table = useReactTable({
    data,
    columns,
    state: { expanded },
    onExpandedChange: setExpanded,
    getSubRows: (row) => row.subRows,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
  });

  const toggleMarketExpanded = (ticker: string) => {
    setExpandedMarkets((prev) => ({
      ...prev,
      [ticker]: !prev[ticker],
    }));
  };

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-sm text-muted-foreground">
          No markets match your search
        </p>
        <button
          type="button"
          onClick={onClearFilters}
          className="text-sm text-primary hover:underline"
        >
          Clear filters
        </button>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {table.getHeaderGroups().map((hg) =>
            hg.headers.map((header) => (
              <TableHead key={header.id}>
                {flexRender(header.column.columnDef.header, header.getContext())}
              </TableHead>
            ))
          )}
        </TableRow>
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.map((row) => (
          <MarketTableRow
            key={row.id}
            row={row}
            expandedMarkets={expandedMarkets}
            onToggleMarket={toggleMarketExpanded}
            columns={columns.length}
          />
        ))}
      </TableBody>
    </Table>
  );
}

function MarketTableRow({
  row,
  expandedMarkets,
  onToggleMarket,
  columns,
}: {
  row: Row<TableRowData>;
  expandedMarkets: Record<string, boolean>;
  onToggleMarket: (ticker: string) => void;
  columns: number;
}) {
  const isEventHeader = row.original.isEventHeader;
  const market = row.original.market;
  const isMarketExpanded = market
    ? expandedMarkets[market.ticker] ?? false
    : false;

  return (
    <>
      <TableRow
        className={
          isEventHeader
            ? "bg-muted/30 hover:bg-muted/50"
            : "cursor-pointer"
        }
        onClick={
          !isEventHeader && market
            ? () => onToggleMarket(market.ticker)
            : undefined
        }
      >
        {isEventHeader ? (
          <TableCell colSpan={columns}>
            {flexRender(
              row.getVisibleCells()[0].column.columnDef.cell,
              row.getVisibleCells()[0].getContext()
            )}
          </TableCell>
        ) : (
          row.getVisibleCells().map((cell) => (
            <TableCell key={cell.id}>
              {flexRender(cell.column.columnDef.cell, cell.getContext())}
            </TableCell>
          ))
        )}
      </TableRow>
      {!isEventHeader && isMarketExpanded && market && (
        <TableRow>
          <TableCell colSpan={columns} className="p-2">
            <CoverageSegmentDetail segments={market.segments} />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
