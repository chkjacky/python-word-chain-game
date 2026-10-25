from sqlalchemy.orm import Session

from app.models.orm import PlayerStatsORM


def upsert_player_stats(
    session: Session,
    username: str,
    games_played: int,
    total_score: int,
    best_score: int,
    by_difficulty: dict,
) -> None:
    session.merge(
        PlayerStatsORM(
            username=username,
            games_played=games_played,
            total_score=total_score,
            best_score=best_score,
            by_difficulty=by_difficulty,
        )
    )
    session.commit()


def get_stats(session: Session, username: str) -> PlayerStatsORM | None:
    return session.get(PlayerStatsORM, username)


def get_leaderboard(session: Session, limit: int = 10) -> list[PlayerStatsORM]:
    return (
        session.query(PlayerStatsORM)
        .order_by(PlayerStatsORM.best_score.desc())
        .limit(limit)
        .all()
    )
