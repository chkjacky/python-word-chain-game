from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.enums import Difficulty
from app.models.orm import Base
from app.services import stats_service


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    return engine


def test_record_game_finished_creates_new_row(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    stats_service.record_game_finished(session, "jacky", Difficulty.MEDIUM, 30, completed=True)
    session.close()

    session = Session(engine)
    result = stats_service.get_stats(session, "jacky")
    session.close()

    assert result.games_played == 1
    assert result.best_score == 30
    assert result.win_rate == 1.0


def test_record_game_finished_accumulates_and_tracks_wins(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    stats_service.record_game_finished(session, "jacky", Difficulty.MEDIUM, 30, completed=True)
    session.close()

    session = Session(engine)
    stats_service.record_game_finished(session, "jacky", Difficulty.MEDIUM, 10, completed=False)
    session.close()

    session = Session(engine)
    result = stats_service.get_stats(session, "jacky")
    session.close()

    assert result.games_played == 2
    assert result.best_score == 30
    assert result.avg_score == 20.0
    assert result.win_rate == 0.5


def test_get_stats_returns_none_for_unknown_user(tmp_path):
    engine = _make_engine(tmp_path)
    session = Session(engine)

    result = stats_service.get_stats(session, "nobody")
    session.close()

    assert result is None


def test_get_leaderboard_derives_difficulty_of_best_score(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    stats_service.record_game_finished(session, "jacky", Difficulty.EASY, 15, completed=True)
    stats_service.record_game_finished(session, "jacky", Difficulty.MEDIUM, 40, completed=True)
    stats_service.record_game_finished(session, "alice", Difficulty.HARD, 25, completed=False)
    session.close()

    session = Session(engine)
    leaderboard = stats_service.get_leaderboard(session, limit=10)
    session.close()

    jacky_entry = next(e for e in leaderboard if e.username == "jacky")
    assert jacky_entry.best_score == 40
    assert jacky_entry.difficulty == Difficulty.MEDIUM

    alice_entry = next(e for e in leaderboard if e.username == "alice")
    assert alice_entry.difficulty == Difficulty.HARD
