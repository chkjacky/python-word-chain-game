"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiRequestError, getStats } from "@/lib/api-client";
import type { Difficulty, StatsResponse } from "@/lib/types";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];

export default function StatsPage() {
  return (
    <Suspense fallback={<StatsSkeleton />}>
      <StatsScreen />
    </Suspense>
  );
}

function StatsScreen() {
  const params = useParams<{ username: string }>();
  const username = decodeURIComponent(params.username);

  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getStats(username);
        if (!cancelled) setStats(res);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Could not load stats.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [username]);

  if (loading) return <StatsSkeleton />;

  if (error || !stats) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <Alert variant="destructive" className="max-w-sm">
          <AlertDescription>
            {error ?? "Could not load stats."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6 py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{stats.username}&apos;s stats</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-4 gap-2 text-center">
            <Stat label="Games" value={stats.games_played} />
            <Stat label="Avg" value={stats.avg_score.toFixed(1)} />
            <Stat label="Best" value={stats.best_score} />
            <Stat
              label="Win %"
              value={`${Math.round(stats.win_rate * 100)}%`}
            />
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Difficulty</TableHead>
                <TableHead>Games</TableHead>
                <TableHead>Wins</TableHead>
                <TableHead>Best</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {DIFFICULTIES.map((d) => {
                const tier = stats.by_difficulty[d];
                return (
                  <TableRow key={d}>
                    <TableCell className="capitalize">{d}</TableCell>
                    <TableCell>{tier?.games ?? 0}</TableCell>
                    <TableCell>{tier?.wins ?? 0}</TableCell>
                    <TableCell>{tier?.best_score ?? 0}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-lg font-semibold">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-12">
      <div className="w-full max-w-md space-y-3">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  );
}
