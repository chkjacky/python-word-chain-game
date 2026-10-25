from pydantic import BaseModel

from app.models.enums import Difficulty, GameStatus


class RetryCounters(BaseModel):
    no_s_retry: int = 0
    json_parse_retry: int = 0
    tool_timeout_retry: int = 0


class TraceEntry(BaseModel):
    step: str
    input: dict | None = None
    tool_calls: list[dict] | None = None
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    outcome: str | None = None
    retries: int | None = None


class ChainSession(BaseModel):
    game_id: str
    username: str
    difficulty: Difficulty
    current_round: int
    total_score: int
    used_words: list[str] = []
    last_letter: str
    cascade_streak: int = 0
    game_status: GameStatus
    retry_counters: RetryCounters = RetryCounters()
    turn_trace: list[TraceEntry] = []
