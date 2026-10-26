from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.chain_session import ChainSession
from app.models.enums import Difficulty, GameStatus
from app.models.orm import Base, TurnORM, TurnTraceORM
from app.repositories.game_repository import (
    append_trace,
    append_turn,
    create_game,
    get_game,
    list_turn_traces,
    save_game_state,
)


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    return engine


def _sample_chain_session(**overrides):
    defaults = dict(
        game_id="gm_1",
        username="jacky",
        difficulty=Difficulty.MEDIUM,
        current_round=1,
        total_score=0,
        used_words=["nectar"],
        last_letter="r",
        cascade_streak=0,
        game_status=GameStatus.IN_PROGRESS,
    )
    defaults.update(overrides)
    return ChainSession(**defaults)


def test_create_game_and_get_game_round_trip_across_session_reopen(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    create_game(session, _sample_chain_session())
    session.close()

    session = Session(engine)
    game = get_game(session, "gm_1")
    session.close()

    assert game is not None
    assert game.username == "jacky"
    assert game.difficulty == Difficulty.MEDIUM
    assert game.used_words == ["nectar"]
    assert game.turn_trace == []


def test_get_game_returns_none_for_unknown_game_id(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    game = get_game(session, "does_not_exist")
    session.close()

    assert game is None


def test_save_game_state_upserts_and_persists_updates(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    create_game(session, _sample_chain_session())
    session.close()

    session = Session(engine)
    updated = _sample_chain_session(current_round=5, total_score=42, last_letter="n")
    save_game_state(session, updated)
    session.close()

    session = Session(engine)
    game = get_game(session, "gm_1")
    session.close()

    assert game.current_round == 5
    assert game.total_score == 42
    assert game.last_letter == "n"


def test_append_turn_persists_turn_row(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    create_game(session, _sample_chain_session())
    append_turn(
        session,
        game_id="gm_1",
        round=1,
        player_word="nectar",
        ai_word="radio",
        score_delta=23,
        score_breakdown={
            "base": 10,
            "creative": 5,
            "cascade": False,
            "length_bonus": 8,
        },
    )
    session.close()

    session = Session(engine)
    turn = session.query(TurnORM).filter_by(game_id="gm_1", round=1).one()
    session.close()

    assert turn.player_word == "nectar"
    assert turn.ai_word == "radio"
    assert turn.score_delta == 23


def test_list_turn_traces_returns_ordered_by_round_then_id(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    create_game(session, _sample_chain_session())
    session.add(
        TurnTraceORM(
            game_id="gm_1",
            round=2,
            step="validate_word",
            model=None,
            tokens_in=0,
            tokens_out=0,
            latency_ms=100,
            cost_usd=0.0,
            outcome="valid",
            raw_json={
                "step": "validate_word",
                "outcome": "valid",
                "latency_ms": 100,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
            },
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
            latency_ms=50,
            cost_usd=0.0,
            outcome="valid",
            raw_json={
                "step": "validate_word",
                "outcome": "valid",
                "latency_ms": 50,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
            },
        )
    )
    session.add(
        TurnTraceORM(
            game_id="gm_1",
            round=1,
            step="generate_ai_move",
            model="gpt-5-mini",
            tokens_in=10,
            tokens_out=5,
            latency_ms=200,
            cost_usd=0.0001,
            outcome="word=radio",
            raw_json={
                "step": "generate_ai_move",
                "outcome": "word=radio",
                "latency_ms": 200,
                "tokens_in": 10,
                "tokens_out": 5,
                "cost_usd": 0.0001,
                "model": "gpt-5-mini",
            },
        )
    )
    session.commit()
    session.close()

    session = Session(engine)
    traces = list_turn_traces(session, "gm_1")
    session.close()

    assert [t.step for t in traces] == [
        "validate_word",
        "generate_ai_move",
        "validate_word",
    ]
    assert traces[0].latency_ms == 50
    assert traces[1].latency_ms == 200
    assert traces[2].latency_ms == 100


def test_append_trace_is_queryable_via_list_turn_traces(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    create_game(session, _sample_chain_session())
    append_trace(
        session,
        "gm_1",
        1,
        {
            "step": "judge_creativity",
            "model": "gpt-5-mini",
            "tokens_in": 20,
            "tokens_out": 8,
            "latency_ms": 150,
            "cost_usd": 0.00005,
            "outcome": "creative=True",
            "retries": 0,
        },
    )
    session.close()

    session = Session(engine)
    traces = list_turn_traces(session, "gm_1")
    session.close()

    assert len(traces) == 1
    assert traces[0].step == "judge_creativity"
    assert traces[0].model == "gpt-5-mini"
    assert traces[0].retries == 0
