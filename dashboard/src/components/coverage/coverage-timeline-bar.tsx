import type { CoverageSegment } from "@/types/api";

function daysBetween(dateA: string, dateB: string): number {
  const a = new Date(dateA);
  const b = new Date(dateB);
  return Math.max(1, Math.round((b.getTime() - a.getTime()) / 86_400_000));
}

interface CoverageTimelineBarProps {
  segments: CoverageSegment[];
  overallStart: string;
  overallEnd: string;
}

export function CoverageTimelineBar({
  segments,
  overallStart,
  overallEnd,
}: CoverageTimelineBarProps) {
  if (segments.length === 0) return null;

  const totalDays = daysBetween(overallStart, overallEnd);

  return (
    <div className="relative h-2 w-full rounded-full bg-muted overflow-hidden">
      {segments.map((seg) => {
        const leftDays = daysBetween(overallStart, seg.segment_start);
        const widthDays = daysBetween(seg.segment_start, seg.segment_end);
        const leftPct = (leftDays / totalDays) * 100;
        const widthPct = (widthDays / totalDays) * 100;

        return (
          <div
            key={seg.segment_id}
            className="absolute top-0 h-full rounded-full bg-primary"
            style={{
              left: `${leftPct}%`,
              width: `max(2px, ${widthPct}%)`,
            }}
          />
        );
      })}
    </div>
  );
}
