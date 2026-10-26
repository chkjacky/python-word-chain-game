import { Alert, AlertDescription } from "@/components/ui/alert";
import type { Difficulty } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AlertTriangle, WifiOff } from "lucide-react";

type Tone = "destructive" | "warning" | "muted";

function describe(
  reason: string,
  difficulty?: Difficulty,
  lastLetter?: string,
): { tone: Tone; message: string } {
  switch (reason) {
    case "wrong_letter":
      return {
        tone: "warning",
        message: `Must start with "${lastLetter ?? "?"}"`,
      };
    case "repeated_word":
      return { tone: "destructive", message: "Already used - game over" };
    case "invalid_length":
      return {
        tone: "warning",
        message: `Out of ${difficulty ?? "the"} length range`,
      };
    case "not_a_real_word":
      return {
        tone: "destructive",
        message: "Not a recognized word - game over",
      };
    case "wrong_difficulty":
      return {
        tone: "warning",
        message: `Too common/uncommon for ${difficulty ?? "this difficulty"}`,
      };
    case "empty_input":
    case "invalid_format":
      return { tone: "muted", message: "Enter a valid word" };
    case "network_error":
      return {
        tone: "destructive",
        message: "Something went wrong - try again",
      };
    default:
      return { tone: "destructive", message: "Rejected - game over" };
  }
}

const toneClasses: Record<Tone, string> = {
  destructive: "",
  warning:
    "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 *:data-[slot=alert-description]:text-amber-600/90 dark:*:data-[slot=alert-description]:text-amber-400/90",
  muted: "border-border bg-muted/50 text-muted-foreground",
};

export function ErrorBanner({
  reason,
  difficulty,
  lastLetter,
}: {
  reason: string;
  difficulty?: Difficulty;
  lastLetter?: string;
}) {
  const { tone, message } = describe(reason, difficulty, lastLetter);

  return (
    <Alert
      variant={tone === "destructive" ? "destructive" : "default"}
      className={cn(tone !== "destructive" && toneClasses[tone])}
    >
      {reason === "network_error" ? <WifiOff /> : <AlertTriangle />}
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
