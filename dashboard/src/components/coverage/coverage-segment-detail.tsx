import { Badge } from "@/components/ui/badge";
import type { CoverageSegment } from "@/types/api";

const compact = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

function formatSegmentRange(start: string, end: string): string {
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

interface CoverageSegmentDetailProps {
  segments: CoverageSegment[];
}

export function CoverageSegmentDetail({
  segments,
}: CoverageSegmentDetailProps) {
  return (
    <div className="flex flex-col gap-2 rounded-md bg-muted/50 p-3">
      {segments.map((seg) => (
        <div
          key={seg.segment_id}
          className="flex items-center justify-between gap-4 text-sm"
        >
          <span className="font-medium">
            {formatSegmentRange(seg.segment_start, seg.segment_end)}
          </span>
          <span className="text-muted-foreground">
            {compact.format(seg.snapshot_count)} snapshots |{" "}
            {compact.format(seg.delta_count)} deltas |{" "}
            {compact.format(seg.trade_count)} trades
          </span>
          <Badge variant="secondary" className="text-xs">
            {seg.days_covered}d
          </Badge>
        </div>
      ))}
    </div>
  );
}
