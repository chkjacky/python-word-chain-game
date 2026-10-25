"use client";

import { CascadeIndicator } from "@/components/chat/CascadeIndicator";
import { DevTracePanel } from "@/components/chat/DevTracePanel";
import { ErrorBanner } from "@/components/chat/ErrorBanner";
import { GameTranscript } from "@/components/chat/GameTranscript";
import type { TranscriptItem } from "@/components/chat/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  ApiRequestError,
  getState,
  getTrace,
  playTurn,
  quitGame,
} from "@/lib/api-client";
import type {
  Difficulty,
  GameStatus,
  ScoreBreakdown,
  TraceEntry,
} from "@/lib/types";
import { Loader2, LogOut, Send } from "lucide-react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const TOTAL_ROUNDS = 10;

function buildInitialItems(usedWords: string[]): TranscriptItem[] {
  return usedWords.map((word, i) => ({
    id: `init-${i}`,
    role: i % 2 === 0 ? "ai" : "player",
    word,
  }));
}

export default function GamePage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-1 flex-col gap-3 p-6">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      }
    >
      <GameScreen />
    </Suspense>
  );
}

function GameScreen() {
  const params = useParams<{ id: string }>();
  const gameId = params.id;

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [username, setUsername] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("easy");
  const [currentRound, setCurrentRound] = useState(1);
  const [totalScore, setTotalScore] = useState(0);
  const [lastLetter, setLastLetter] = useState("");
  const [cascadeStreak, setCascadeStreak] = useState(0);
  const [gameStatus, setGameStatus] = useState<GameStatus>("in_progress");

  const [items, setItems] = useState<TranscriptItem[]>([]);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const [devMode, setDevMode] = useState(false);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);
  const [gameNotFound, setGameNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const state = await getState(gameId);
        if (cancelled) return;
        setUsername(state.username);
        setDifficulty(state.difficulty);
        setCurrentRound(state.current_round);
        setTotalScore(state.total_score);
        setLastLetter(state.last_letter);
        setCascadeStreak(state.cascade_streak);
        setGameStatus(state.game_status);
        setItems(buildInitialItems(state.used_words));
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setGameNotFound(true);
          return;
        }
        setLoadError(
          err instanceof ApiRequestError
            ? err.message
            : "Could not load this game.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [gameId]);

  async function refreshTrace() {
    setTraceLoading(true);
    try {
      const res = await getTrace(gameId);
      setTrace(res.trace);
    } catch {
      // dev panel is best-effort; keep whatever we had
    } finally {
      setTraceLoading(false);
    }
  }

  useEffect(() => {
    if (devMode) void refreshTrace();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devMode]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const word = input.trim();
    if (!word || submitting || gameStatus !== "in_progress") return;

    setSubmitting(true);
    setNetworkError(null);
    const letterAtSubmit = lastLetter;

    try {
      const res = await playTurn(gameId, { word });
      setInput("");

      if (res.accepted) {
        const breakdown = res.score_breakdown as ScoreBreakdown;
        const delta = res.score_delta ?? 0;
        const newStreak = breakdown.creative > 0 ? cascadeStreak + 1 : 0;

        setCascadeStreak(newStreak);
        setTotalScore((s) => s + delta);
        if (res.ai_move) setLastLetter(res.ai_move[res.ai_move.length - 1]);
        setCurrentRound((res.round ?? currentRound) + 1);
        setItems((prev) => [
          ...prev,
          {
            id: `p-${res.round}`,
            role: "player",
            word,
            scoreDelta: delta,
            breakdown,
          },
          ...(res.ai_move
            ? [
                {
                  id: `a-${res.round}`,
                  role: "ai",
                  word: res.ai_move,
                } as TranscriptItem,
              ]
            : []),
        ]);
      } else {
        setItems((prev) => [
          ...prev,
          {
            id: `r-${Date.now()}`,
            role: "player",
            word,
            reason: res.reason ?? "unknown",
            lastLetterAtSubmit: letterAtSubmit,
          },
        ]);
      }

      setGameStatus(res.game_status);
      if (devMode) void refreshTrace();
    } catch (err) {
      setNetworkError(
        err instanceof ApiRequestError
          ? err.message
          : "Something went wrong — try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleQuit() {
    try {
      const res = await quitGame(gameId);
      setGameStatus(res.game_status);
      setTotalScore(res.final_score);
    } catch (err) {
      setNetworkError(
        err instanceof ApiRequestError
          ? err.message
          : "Something went wrong — try again.",
      );
    }
  }

  if (gameNotFound) {
    notFound();
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col gap-3 p-6">
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <Alert variant="destructive" className="max-w-sm">
          <AlertDescription>{loadError}</AlertDescription>
        </Alert>
      </div>
    );
  }

  const ended = gameStatus !== "in_progress";

  return (
    <div className="flex min-h-0 flex-1 flex-col mx-120 border rounded-lg mt-5 mb-5">
      <div className="flex shrink-0 flex-wrap w-1/3  items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{username}</span> ·{" "}
          {difficulty} · round {Math.min(currentRound, TOTAL_ROUNDS)}/
          {TOTAL_ROUNDS}
        </div>
        <div className="flex items-center gap-2">
          <Label htmlFor="dev-mode" className="text-sm text-muted-foreground">
            Dev mode
          </Label>
          <Switch
            id="dev-mode"
            checked={devMode}
            onCheckedChange={setDevMode}
            className="cursor-pointer"
          />
        </div>
      </div>

      <div className="shrink-0 px-4 py-2">
        <CascadeIndicator streak={cascadeStreak} />
      </div>
      <Separator className="shrink-0" />

      <GameTranscript items={items} difficulty={difficulty} />

      <div className="flex shrink-0 flex-col gap-2 border-t border-border p-4">
        {networkError && <ErrorBanner reason="network_error" />}

        {ended ? (
          <div className="flex flex-col items-center gap-3 text-center">
            <p className="text-sm font-medium">
              {gameStatus === "quit" ? "Quit" : "Game over"} · final score{" "}
              {totalScore}
            </p>
            <div className="flex gap-2">
              <Button asChild variant="outline">
                <Link href={`/stats/${encodeURIComponent(username)}`}>
                  View stats
                </Link>
              </Button>
              <Button asChild>
                <Link href="/">Play again</Link>
              </Button>
            </div>
          </div>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
              <InputGroup>
                <InputGroupInput
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={`Starts with "${lastLetter}"...`}
                  disabled={submitting}
                  maxLength={60}
                  autoFocus
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    type="submit"
                    disabled={submitting || !input.trim()}
                    className="cursor-pointer"
                  >
                    {submitting ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <Send />
                    )}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
            </form>
            <Button
              variant="ghost"
              size="sm"
              className="self-start cursor-pointer"
              onClick={handleQuit}
            >
              <LogOut />
              Quit game
            </Button>
          </>
        )}
      </div>

      {devMode && (
        <div className="max-h-48 shrink-0 overflow-y-auto border-t border-border">
          <div className="px-4 py-2 text-xs font-medium text-muted-foreground">
            Dev trace — round {Math.min(currentRound, TOTAL_ROUNDS)}
          </div>
          <DevTracePanel trace={trace} loading={traceLoading} />
        </div>
      )}
    </div>
  );
}
