"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { ApiRequestError, startGame } from "@/lib/api-client";
import type { Difficulty } from "@/lib/types";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

const DIFFICULTIES: { value: Difficulty; label: string; range: string }[] = [
  { value: "easy", label: "Easy", range: "4-6" },
  { value: "medium", label: "Medium", range: "6-8" },
  { value: "hard", label: "Hard", range: "8-12" },
];

export default function Home() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("easy");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) {
      setError("Enter a username to start.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await startGame({ username: trimmed, difficulty });
      setLoading(false);
      router.push(`/game/${res.game_id}`);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Something went wrong - try again.",
      );
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Start a new game</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="flex flex-col gap-4 mb-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                maxLength={32}
                disabled={loading}
                autoFocus
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label>Difficulty</Label>
              <ToggleGroup
                type="single"
                variant="outline"
                value={difficulty}
                onValueChange={(value) => {
                  if (value) setDifficulty(value as Difficulty);
                }}
                className="w-full"
                disabled={loading}
              >
                {DIFFICULTIES.map((d) => (
                  <ToggleGroupItem
                    key={d.value}
                    value={d.value}
                    className="flex-1 flex-col gap-0 py-1 cursor-pointer h-fit"
                  >
                    <span className="text-sm font-medium">{d.label}</span>
                    <span className="text-xs text-muted-foreground">
                      {d.range}
                    </span>
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertTriangle />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full cursor-pointer"
              disabled={loading}
            >
              {loading && <Loader2 className="animate-spin" />}
              Start Game
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
