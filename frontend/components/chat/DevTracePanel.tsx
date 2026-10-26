import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { TraceEntry } from "@/lib/types";

export function DevTracePanel({
  trace,
  loading,
}: {
  trace: TraceEntry[];
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="flex flex-col gap-1.5 p-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    );
  }

  if (trace.length === 0) {
    return (
      <p className="p-3 text-sm text-muted-foreground">No trace entries yet.</p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>step</TableHead>
          <TableHead>model</TableHead>
          <TableHead>tok in/out</TableHead>
          <TableHead>ms</TableHead>
          <TableHead>cost $</TableHead>
          <TableHead>outcome</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {trace.map((entry, i) => (
          <TableRow key={i}>
            <TableCell className="font-medium">{entry.step}</TableCell>
            <TableCell className="text-muted-foreground">
              {entry.model ?? "-"}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {entry.tokens_in}/{entry.tokens_out}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {entry.latency_ms}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {entry.cost_usd.toFixed(5)}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {entry.outcome ?? "-"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
