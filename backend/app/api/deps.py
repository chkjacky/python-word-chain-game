from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.errors import GameNotFoundError
from app.db.session import SessionLocal
from app.models.chain_session import ChainSession
from app.repositories import game_repository


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_game_or_404(game_id: str, db: Session = Depends(get_db)) -> ChainSession:
    chain_session = game_repository.get_game(db, game_id)
    if chain_session is None:
        raise GameNotFoundError(f"no such game: {game_id}")
    return chain_session
