from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.orm import Base
from app.repositories.stats_repository import get_leaderboard, get_stats, upsert_player_stats


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    return engine


def test_upsert_player_stats_inserts_new_row(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    upsert_player_stats(session, "jacky", games_played=1, total_score=30, best_score=30,
                         by_difficulty={"medium": {"games": 1}})
    session.close()

    session = Session(engine)
    stats = get_stats(session, "jacky")
    session.close()

    assert stats is not None
    assert stats.games_played == 1
    assert stats.best_score == 30


def test_upsert_player_stats_updates_existing_row(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    upsert_player_stats(session, "jacky", games_played=1, total_score=30, best_score=30,
                         by_difficulty={"medium": {"games": 1}})
    session.close()

    session = Session(engine)
    upsert_player_stats(session, "jacky", games_played=2, total_score=70, best_score=40,
                         by_difficulty={"medium": {"games": 2}})
    session.close()

    session = Session(engine)
    stats = get_stats(session, "jacky")
    all_rows = session.query(type(stats)).all()
    session.close()

    assert stats.games_played == 2
    assert stats.best_score == 40
    assert len(all_rows) == 1


def test_get_stats_returns_none_for_unknown_username(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    stats = get_stats(session, "nobody")
    session.close()

    assert stats is None


def test_get_leaderboard_returns_top_n_ordered_by_best_score(tmp_path):
    engine = _make_engine(tmp_path)

    session = Session(engine)
    upsert_player_stats(session, "alice", games_played=1, total_score=10, best_score=10, by_difficulty={})
    upsert_player_stats(session, "bob", games_played=1, total_score=50, best_score=50, by_difficulty={})
    upsert_player_stats(session, "carol", games_played=1, total_score=30, best_score=30, by_difficulty={})
    upsert_player_stats(session, "dave", games_played=1, total_score=20, best_score=20, by_difficulty={})
    session.close()

    session = Session(engine)
    leaderboard = get_leaderboard(session, limit=2)
    session.close()

    assert len(leaderboard) == 2
    assert [p.username for p in leaderboard] == ["bob", "carol"]
