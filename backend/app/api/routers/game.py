from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_game_or_404
from app.models.api import (
    GameStateResponse,
    QuitResponse,
    StartGameRequest,
    StartGameResponse,
    TraceResponse,
    TurnRequest,
    TurnResponse,
)
from app.models.chain_session import ChainSession
from app.repositories import game_repository
from app.services import game_service

router = APIRouter(prefix="/game", tags=["game"])


@router.post("/start", response_model=StartGameResponse)
async def start_game_route(request: StartGameRequest, db: Session = Depends(get_db)) -> StartGameResponse:
    chain_session = await game_service.start_game(db, request.username, request.difficulty)
    return StartGameResponse(
        game_id=chain_session.game_id,
        ai_opening_word=chain_session.used_words[0],
        chain_session_snapshot=chain_session,
    )


@router.post("/{game_id}/turn", response_model=TurnResponse)
async def play_turn_route(game_id: str, request: TurnRequest, db: Session = Depends(get_db)) -> TurnResponse:
    return await game_service.play_turn(db, game_id, request.word)


@router.get("/{game_id}/state", response_model=GameStateResponse)
async def get_state_route(chain_session: ChainSession = Depends(get_game_or_404)) -> GameStateResponse:
    return GameStateResponse(**chain_session.model_dump(exclude={"turn_trace", "retry_counters"}))


@router.get("/{game_id}/trace", response_model=TraceResponse)
async def get_trace_route(
    game_id: str,
    chain_session: ChainSession = Depends(get_game_or_404),
    db: Session = Depends(get_db),
) -> TraceResponse:
    return TraceResponse(game_id=game_id, trace=game_repository.list_turn_traces(db, game_id))


@router.post("/{game_id}/quit", response_model=QuitResponse)
def quit_game_route(game_id: str, db: Session = Depends(get_db)) -> QuitResponse:
    return game_service.quit_game(db, game_id)
