import type { ScoreBreakdown } from "@/lib/types";

export interface TranscriptItem {
  id: string;
  role: "ai" | "player";
  word: string;
  scoreDelta?: number;
  breakdown?: ScoreBreakdown;
  reason?: string;
  lastLetterAtSubmit?: string;
}
