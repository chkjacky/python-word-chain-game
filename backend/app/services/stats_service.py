from app.models.api import LeaderboardEntry, StatsResponse
from app.models.enums import Difficulty
from app.repositories import stats_repository


def record_game_finished(session, username: str, difficulty: Difficulty, final_score: int, completed: bool) -> None:
    existing = stats_repository.get_stats(session, username)
    by_difficulty = dict(existing.by_difficulty) if existing else {}
    tier = by_difficulty.get(difficulty.value, {"games": 0, "wins": 0, "best_score": 0})
    by_difficulty[difficulty.value] = {
        "games": tier["games"] + 1,
        "wins": tier["wins"] + (1 if completed else 0),
        "best_score": max(tier["best_score"], final_score),
    }

    games_played = (existing.games_played if existing else 0) + 1
    total_score = (existing.total_score if existing else 0) + final_score
    best_score = max(existing.best_score if existing else 0, final_score)

    stats_repository.upsert_player_stats(session, username, games_played, total_score, best_score, by_difficulty)


def get_stats(session, username: str) -> StatsResponse | None:
    stats = stats_repository.get_stats(session, username)
    if stats is None:
        return None
    total_games = sum(tier["games"] for tier in stats.by_difficulty.values()) or stats.games_played
    total_wins = sum(tier.get("wins", 0) for tier in stats.by_difficulty.values())
    return StatsResponse(
        username=username,
        games_played=stats.games_played,
        avg_score=stats.total_score / stats.games_played if stats.games_played else 0.0,
        best_score=stats.best_score,
        win_rate=total_wins / total_games if total_games else 0.0,
        by_difficulty=stats.by_difficulty,
    )


def get_leaderboard(session, limit: int = 10) -> list[LeaderboardEntry]:
    rows = stats_repository.get_leaderboard(session, limit)
    entries = []
    for row in rows:
        best_tier = max(row.by_difficulty.items(), key=lambda kv: kv[1]["best_score"], default=(None, None))[0]
        entries.append(
            LeaderboardEntry(
                username=row.username,
                best_score=row.best_score,
                difficulty=Difficulty(best_tier) if best_tier else Difficulty.EASY,
            )
        )
    return entries
