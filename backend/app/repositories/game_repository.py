from sqlalchemy.orm import Session

from app.models.chain_session import ChainSession, TraceEntry
from app.models.orm import GameORM, TurnORM, TurnTraceORM


def _to_chain_session(game: GameORM) -> ChainSession:
    return ChainSession(
        game_id=game.game_id,
        username=game.username,
        difficulty=game.difficulty,
        current_round=game.current_round,
        total_score=game.total_score,
        used_words=game.used_words,
        last_letter=game.last_letter,
        cascade_streak=game.cascade_streak,
        game_status=game.game_status,
        retry_counters=game.retry_counters,
    )


def _to_game_orm(chain_session: ChainSession) -> GameORM:
    return GameORM(
        game_id=chain_session.game_id,
        username=chain_session.username,
        difficulty=chain_session.difficulty.value,
        current_round=chain_session.current_round,
        total_score=chain_session.total_score,
        used_words=chain_session.used_words,
        last_letter=chain_session.last_letter,
        cascade_streak=chain_session.cascade_streak,
        game_status=chain_session.game_status.value,
        retry_counters=chain_session.retry_counters.model_dump(),
    )


def create_game(session: Session, chain_session: ChainSession) -> None:
    session.add(_to_game_orm(chain_session))
    session.commit()


def get_game(session: Session, game_id: str) -> ChainSession | None:
    game = session.get(GameORM, game_id)
    return _to_chain_session(game) if game else None


def save_game_state(session: Session, chain_session: ChainSession) -> None:
    session.merge(_to_game_orm(chain_session))
    session.commit()


def append_turn(
    session: Session,
    game_id: str,
    round: int,
    player_word: str,
    ai_word: str,
    score_delta: int,
    score_breakdown: dict,
) -> None:
    session.add(
        TurnORM(
            game_id=game_id,
            round=round,
            player_word=player_word,
            ai_word=ai_word,
            score_delta=score_delta,
            score_breakdown=score_breakdown,
        )
    )
    session.commit()


def append_trace(session: Session, game_id: str, round: int, record: dict) -> None:
    session.add(
        TurnTraceORM(
            game_id=game_id,
            round=round,
            step=record.get("step", ""),
            model=record.get("model"),
            tokens_in=record.get("tokens_in", 0),
            tokens_out=record.get("tokens_out", 0),
            latency_ms=record.get("latency_ms", 0),
            cost_usd=record.get("cost_usd", 0.0),
            outcome=record.get("outcome"),
            raw_json=record,
        )
    )
    session.commit()


def list_turn_traces(session: Session, game_id: str) -> list[TraceEntry]:
    rows = (
        session.query(TurnTraceORM)
        .filter_by(game_id=game_id)
        .order_by(TurnTraceORM.round, TurnTraceORM.id)
        .all()
    )
    return [TraceEntry.model_validate(row.raw_json) for row in rows]
