from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.orm import Base, GameORM, PlayerStatsORM, TurnORM, TurnTraceORM


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    return engine


def test_game_orm_round_trip(tmp_path):
    engine = _make_engine(tmp_path)

    with Session(engine) as session:
        session.add(
            GameORM(
                game_id="gm_1",
                username="jacky",
                difficulty="medium",
                current_round=4,
                total_score=37,
                used_words=["dragon", "nectar"],
                last_letter="n",
                cascade_streak=2,
                game_status="in_progress",
                retry_counters={"no_s_retry": 0, "json_parse_retry": 1, "tool_timeout_retry": 0},
            )
        )
        session.commit()

    with Session(engine) as session:
        game = session.get(GameORM, "gm_1")
        assert game is not None
        assert game.username == "jacky"
        assert game.used_words == ["dragon", "nectar"]
        assert game.retry_counters == {"no_s_retry": 0, "json_parse_retry": 1, "tool_timeout_retry": 0}
        assert game.created_at is not None


def test_turn_orm_round_trip(tmp_path):
    engine = _make_engine(tmp_path)

    with Session(engine) as session:
        session.add(
            GameORM(
                game_id="gm_1",
                username="jacky",
                difficulty="medium",
                current_round=1,
                total_score=0,
                used_words=[],
                last_letter="a",
                cascade_streak=0,
                game_status="in_progress",
                retry_counters={},
            )
        )
        session.add(
            TurnORM(
                game_id="gm_1",
                round=1,
                player_word="nectar",
                ai_word="radio",
                score_delta=23,
                score_breakdown={"base": 10, "creative": 5, "cascade": False, "length_bonus": 8},
            )
        )
        session.commit()

    with Session(engine) as session:
        turn = session.query(TurnORM).filter_by(game_id="gm_1", round=1).one()
        assert turn.player_word == "nectar"
        assert turn.ai_word == "radio"
        assert turn.score_delta == 23
        assert turn.score_breakdown["length_bonus"] == 8


def test_turn_trace_orm_round_trip(tmp_path):
    engine = _make_engine(tmp_path)

    with Session(engine) as session:
        session.add(
            GameORM(
                game_id="gm_1",
                username="jacky",
                difficulty="medium",
                current_round=1,
                total_score=0,
                used_words=[],
                last_letter="a",
                cascade_streak=0,
                game_status="in_progress",
                retry_counters={},
            )
        )
        session.add(
            TurnTraceORM(
                game_id="gm_1",
                round=1,
                step="validate_word",
                model=None,
                tokens_in=0,
                tokens_out=0,
                latency_ms=215,
                cost_usd=0.0,
                outcome="valid",
                raw_json={"step": "validate_word", "outcome": "valid"},
            )
        )
        session.commit()

    with Session(engine) as session:
        trace = session.query(TurnTraceORM).filter_by(game_id="gm_1", round=1).one()
        assert trace.step == "validate_word"
        assert trace.model is None
        assert trace.latency_ms == 215
        assert trace.raw_json == {"step": "validate_word", "outcome": "valid"}


def test_player_stats_orm_round_trip(tmp_path):
    engine = _make_engine(tmp_path)

    with Session(engine) as session:
        session.add(
            PlayerStatsORM(
                username="jacky",
                games_played=3,
                total_score=90,
                best_score=40,
                by_difficulty={"easy": {"games": 1}, "medium": {"games": 2}},
            )
        )
        session.commit()

    with Session(engine) as session:
        stats = session.get(PlayerStatsORM, "jacky")
        assert stats is not None
        assert stats.games_played == 3
        assert stats.best_score == 40
        assert stats.by_difficulty == {"easy": {"games": 1}, "medium": {"games": 2}}
