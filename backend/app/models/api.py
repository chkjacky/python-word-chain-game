from pydantic import BaseModel

from app.domain.scoring import ScoreBreakdown
from app.models.chain_session import ChainSession, TraceEntry
from app.models.enums import Difficulty, GameStatus


class StartGameRequest(BaseModel):
    username: str
    difficulty: Difficulty


class StartGameResponse(BaseModel):
    game_id: str
    ai_opening_word: str
    chain_session_snapshot: ChainSession


class TurnRequest(BaseModel):
    word: str


class TurnResponse(BaseModel):
    accepted: bool
    score_delta: int | None = None
    score_breakdown: ScoreBreakdown | None = None
    ai_move: str | None = None
    game_status: GameStatus
    round: int | None = None
    reason: str | None = None


class GameStateResponse(BaseModel):
    game_id: str
    username: str
    difficulty: Difficulty
    current_round: int
    total_score: int
    used_words: list[str] = []
    last_letter: str
    cascade_streak: int = 0
    game_status: GameStatus


class TraceResponse(BaseModel):
    game_id: str
    trace: list[TraceEntry]


class QuitResponse(BaseModel):
    game_status: GameStatus
    final_score: int


class StatsResponse(BaseModel):
    username: str
    games_played: int
    avg_score: float
    best_score: int
    win_rate: float
    by_difficulty: dict


class LeaderboardEntry(BaseModel):
    username: str
    best_score: int
    difficulty: Difficulty
