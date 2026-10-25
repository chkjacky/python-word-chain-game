import { cn } from "@/lib/utils";
import { Flame } from "lucide-react";

export function CascadeIndicator({ streak }: { streak: number }) {
  const filled = streak === 0 ? 0 : ((streak - 1) % 3) + 1;

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <div className="flex items-center gap-0.5">
        {[1, 2, 3].map((slot) => (
          <Flame
            key={slot}
            className={cn(
              "h-4 w-4",
              slot <= filled
                ? "fill-orange-500 text-orange-500"
                : "text-muted-foreground/30",
            )}
          />
        ))}
      </div>
      <span>{filled}/3 toward ×2 cascade</span>
    </div>
  );
}
