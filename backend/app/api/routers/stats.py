from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.api import LeaderboardEntry, StatsResponse
from app.services import stats_service

router = APIRouter(tags=["stats"])


@router.get("/stats/{username}", response_model=StatsResponse)
def get_stats_route(username: str, db: Session = Depends(get_db)) -> StatsResponse:
    stats = stats_service.get_stats(db, username)
    if stats is not None:
        return stats
    return StatsResponse(
        username=username, games_played=0, avg_score=0.0, best_score=0, win_rate=0.0, by_difficulty={}
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard_route(db: Session = Depends(get_db)) -> list[LeaderboardEntry]:
    return stats_service.get_leaderboard(db)
