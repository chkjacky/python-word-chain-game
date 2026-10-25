import { Badge } from "@/components/ui/badge";
import type { ScoreBreakdown } from "@/lib/types";

export function ScoreChip({
  delta,
  breakdown,
}: {
  delta: number;
  breakdown: ScoreBreakdown;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <Badge>+{delta}</Badge>
      <Badge variant="outline">{breakdown.base} base</Badge>
      {breakdown.creative > 0 && (
        <Badge variant="secondary">+{breakdown.creative} creative</Badge>
      )}
      {breakdown.cascade && <Badge variant="default">×2 cascade</Badge>}
      {breakdown.length_bonus > 0 && (
        <Badge variant="outline">+{breakdown.length_bonus} len</Badge>
      )}
    </div>
  );
}
