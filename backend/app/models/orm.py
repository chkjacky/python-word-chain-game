from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GameORM(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(primary_key=True)
    username: Mapped[str]
    difficulty: Mapped[str]
    current_round: Mapped[int]
    total_score: Mapped[int]
    used_words: Mapped[list] = mapped_column(JSON)
    last_letter: Mapped[str]
    cascade_streak: Mapped[int]
    game_status: Mapped[str]
    retry_counters: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class TurnORM(Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.game_id"))
    round: Mapped[int]
    player_word: Mapped[str]
    ai_word: Mapped[str]
    score_delta: Mapped[int]
    score_breakdown: Mapped[dict] = mapped_column(JSON)


class TurnTraceORM(Base):
    __tablename__ = "turn_traces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.game_id"))
    round: Mapped[int]
    step: Mapped[str]
    model: Mapped[str | None]
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    latency_ms: Mapped[int]
    cost_usd: Mapped[float]
    outcome: Mapped[str | None]
    raw_json: Mapped[dict] = mapped_column(JSON)


class PlayerStatsORM(Base):
    __tablename__ = "player_stats"

    username: Mapped[str] = mapped_column(primary_key=True)
    games_played: Mapped[int] = mapped_column(default=0)
    total_score: Mapped[int] = mapped_column(default=0)
    best_score: Mapped[int] = mapped_column(default=0)
    by_difficulty: Mapped[dict] = mapped_column(JSON, default=dict)
