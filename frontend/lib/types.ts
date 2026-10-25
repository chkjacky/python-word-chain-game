export type Difficulty = "easy" | "medium" | "hard";

export type GameStatus = "in_progress" | "ended" | "quit";

export type RejectionReason =
  | "empty_input"
  | "invalid_format"
  | "wrong_letter"
  | "repeated_word"
  | "invalid_length"
  | "not_a_real_word"
  | "wrong_difficulty";

export interface RetryCounters {
  no_s_retry: number;
  json_parse_retry: number;
  tool_timeout_retry: number;
}

export interface TraceEntry {
  step: string;
  input?: Record<string, unknown> | null;
  tool_calls?: Record<string, unknown>[] | null;
  model?: string | null;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  cost_usd: number;
  outcome?: string | null;
  retries?: number | null;
}

export interface ChainSession {
  game_id: string;
  username: string;
  difficulty: Difficulty;
  current_round: number;
  total_score: number;
  used_words: string[];
  last_letter: string;
  cascade_streak: number;
  game_status: GameStatus;
  retry_counters: RetryCounters;
  turn_trace: TraceEntry[];
}

export interface ScoreBreakdown {
  base: number;
  creative: number;
  cascade: boolean;
  length_bonus: number;
}

export interface StartGameRequest {
  username: string;
  difficulty: Difficulty;
}

export interface StartGameResponse {
  game_id: string;
  ai_opening_word: string;
  chain_session_snapshot: ChainSession;
}

export interface TurnRequest {
  word: string;
}

export interface TurnResponse {
  accepted: boolean;
  score_delta?: number | null;
  score_breakdown?: ScoreBreakdown | null;
  ai_move?: string | null;
  game_status: GameStatus;
  round?: number | null;
  reason?: RejectionReason | string | null;
}

export interface GameStateResponse {
  game_id: string;
  username: string;
  difficulty: Difficulty;
  current_round: number;
  total_score: number;
  used_words: string[];
  last_letter: string;
  cascade_streak: number;
  game_status: GameStatus;
}

export interface TraceResponse {
  game_id: string;
  trace: TraceEntry[];
}

export interface QuitResponse {
  game_status: GameStatus;
  final_score: number;
}

export interface DifficultyStats {
  games: number;
  wins: number;
  best_score: number;
}

export interface StatsResponse {
  username: string;
  games_played: number;
  avg_score: number;
  best_score: number;
  win_rate: number;
  by_difficulty: Record<string, DifficultyStats>;
}

export interface LeaderboardEntry {
  username: string;
  best_score: number;
  difficulty: Difficulty;
}

export interface ApiError {
  code: string;
  message: string;
  status: number;
}
