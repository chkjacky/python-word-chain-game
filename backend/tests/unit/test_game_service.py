from unittest.mock import AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.orchestrator import TurnAgentResult
from app.core.errors import GameNotFoundError
from app.models.enums import Difficulty, GameStatus
from app.models.orm import Base
from app.repositories import game_repository, stats_repository
from app.services import game_service


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    return engine


async def test_start_game_generates_opening_word_and_persists(tmp_path, monkeypatch):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    session.close()

    assert chain_session.used_words == ["dragon"]
    assert chain_session.last_letter == "n"

    session = Session(engine)
    persisted = game_repository.get_game(session, chain_session.game_id)
    session.close()

    assert persisted.used_words == ["dragon"]
    assert persisted.last_letter == "n"
    assert persisted.current_round == 1


async def test_play_turn_happy_path_updates_and_persists(tmp_path, monkeypatch):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )
    monkeypatch.setattr(
        game_service,
        "run_turn",
        AsyncMock(
            return_value=TurnAgentResult(
                valid=True, creative=True, creativity_reason="clever", ai_word="radio"
            )
        ),
    )

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    session.close()

    session = Session(engine)
    result = await game_service.play_turn(session, chain_session.game_id, "nectar")
    session.close()

    assert result.accepted is True
    assert result.ai_move == "radio"
    assert result.score_breakdown.creative == 5
    assert result.round == 1

    session = Session(engine)
    persisted = game_repository.get_game(session, chain_session.game_id)
    session.close()

    assert persisted.current_round == 2
    assert persisted.total_score == result.score_delta
    assert persisted.used_words == ["dragon", "nectar", "radio"]
    assert persisted.last_letter == "o"
    assert persisted.cascade_streak == 1


async def test_play_turn_invalid_word_ends_game(tmp_path, monkeypatch):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )
    monkeypatch.setattr(
        game_service,
        "run_turn",
        AsyncMock(return_value=TurnAgentResult(valid=False, reason="wrong_letter")),
    )

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    session.close()

    session = Session(engine)
    result = await game_service.play_turn(session, chain_session.game_id, "radio")
    session.close()

    assert result.accepted is False
    assert result.reason == "wrong_letter"
    assert result.game_status == GameStatus.ENDED

    session = Session(engine)
    persisted = game_repository.get_game(session, chain_session.game_id)
    stats = stats_repository.get_stats(session, "jacky")
    session.close()

    assert persisted.game_status == GameStatus.ENDED
    assert stats.by_difficulty["medium"]["wins"] == 0


async def test_play_turn_completing_round_10_ends_game_and_records_win(
    tmp_path, monkeypatch
):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )
    monkeypatch.setattr(
        game_service,
        "run_turn",
        AsyncMock(
            return_value=TurnAgentResult(valid=True, creative=False, ai_word="radio")
        ),
    )

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    chain_session.current_round = 10
    game_repository.save_game_state(session, chain_session)
    session.close()

    session = Session(engine)
    result = await game_service.play_turn(session, chain_session.game_id, "nectar")
    session.close()

    assert result.game_status == GameStatus.ENDED

    session = Session(engine)
    stats = stats_repository.get_stats(session, "jacky")
    session.close()

    assert stats.by_difficulty["medium"]["wins"] == 1


async def test_play_turn_unknown_game_raises(tmp_path):
    engine = _make_engine(tmp_path)
    session = Session(engine)

    try:
        await game_service.play_turn(session, "does_not_exist", "nectar")
        assert False, "expected GameNotFoundError"
    except GameNotFoundError:
        pass
    finally:
        session.close()


async def test_play_turn_on_already_ended_game_short_circuits(tmp_path, monkeypatch):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )
    run_turn_mock = AsyncMock()
    monkeypatch.setattr(game_service, "run_turn", run_turn_mock)

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    chain_session.game_status = GameStatus.ENDED
    game_repository.save_game_state(session, chain_session)
    session.close()

    session = Session(engine)
    result = await game_service.play_turn(session, chain_session.game_id, "nectar")
    session.close()

    assert result.accepted is False
    assert result.reason == "game_already_ended"
    run_turn_mock.assert_not_called()


async def test_quit_game_sets_status_and_records_stats(tmp_path, monkeypatch):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    session.close()

    session = Session(engine)
    result = game_service.quit_game(session, chain_session.game_id)
    session.close()

    assert result.game_status == GameStatus.QUIT
    assert result.final_score == 0

    session = Session(engine)
    persisted = game_repository.get_game(session, chain_session.game_id)
    stats = stats_repository.get_stats(session, "jacky")
    session.close()

    assert persisted.game_status == GameStatus.QUIT
    assert stats.by_difficulty["medium"]["wins"] == 0


async def test_quit_game_is_idempotent_and_does_not_double_count_stats(
    tmp_path, monkeypatch
):
    engine = _make_engine(tmp_path)
    monkeypatch.setattr(
        game_service.move_generator_agent,
        "generate_move",
        AsyncMock(return_value="dragon"),
    )

    session = Session(engine)
    chain_session = await game_service.start_game(session, "jacky", Difficulty.MEDIUM)
    session.close()

    session = Session(engine)
    first = game_service.quit_game(session, chain_session.game_id)
    session.close()

    session = Session(engine)
    second = game_service.quit_game(session, chain_session.game_id)
    session.close()

    assert first.game_status == GameStatus.QUIT
    assert second.game_status == GameStatus.QUIT
    assert second.final_score == first.final_score

    session = Session(engine)
    stats = stats_repository.get_stats(session, "jacky")
    session.close()

    assert stats.games_played == 1
