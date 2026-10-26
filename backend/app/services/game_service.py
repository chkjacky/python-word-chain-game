import uuid

from app.agents.move_generator_agent import move_generator_agent
from app.agents.orchestrator import run_turn
from app.core.errors import GameNotFoundError
from app.domain.scoring import score_turn
from app.models.api import QuitResponse, TurnResponse
from app.models.chain_session import ChainSession, RetryCounters
from app.models.enums import Difficulty, GameStatus
from app.repositories import game_repository
from app.services import stats_service

TOTAL_ROUNDS = 10


async def start_game(session, username: str, difficulty: Difficulty) -> ChainSession:
    game_id = f"gm_{uuid.uuid4().hex[:8]}"
    draft = ChainSession(
        game_id=game_id,
        username=username,
        difficulty=difficulty,
        current_round=1,
        total_score=0,
        used_words=[],
        last_letter="",
        cascade_streak=0,
        game_status=GameStatus.IN_PROGRESS,
        retry_counters=RetryCounters(),
    )
    opening_word = await move_generator_agent.generate_move(draft)
    chain_session = draft.model_copy(
        update={"used_words": [opening_word], "last_letter": opening_word[-1]}
    )
    game_repository.create_game(session, chain_session)
    for entry in draft.turn_trace:
        game_repository.append_trace(session, game_id, 0, entry.model_dump())
    return chain_session


async def play_turn(session, game_id: str, word: str) -> TurnResponse:
    chain_session = game_repository.get_game(session, game_id)
    if chain_session is None:
        raise GameNotFoundError(f"no such game: {game_id}")

    if chain_session.game_status != GameStatus.IN_PROGRESS:
        return TurnResponse(
            accepted=False,
            reason="game_already_ended",
            game_status=chain_session.game_status,
            round=chain_session.current_round,
        )

    agent_result = await run_turn(chain_session, word)
    round_played = chain_session.current_round

    for entry in chain_session.turn_trace:
        game_repository.append_trace(session, game_id, round_played, entry.model_dump())

    if not agent_result.valid:
        chain_session.game_status = GameStatus.ENDED
        game_repository.save_game_state(session, chain_session)
        stats_service.record_game_finished(
            session,
            chain_session.username,
            chain_session.difficulty,
            chain_session.total_score,
            completed=False,
        )
        return TurnResponse(
            accepted=False,
            reason=agent_result.reason,
            game_status=GameStatus.ENDED,
            round=round_played,
        )

    new_streak = chain_session.cascade_streak + 1 if agent_result.creative else 0
    score_delta, breakdown = score_turn(word, agent_result.creative, new_streak)

    chain_session.total_score += score_delta
    chain_session.used_words += [word, agent_result.ai_word]
    chain_session.last_letter = agent_result.ai_word[-1]
    chain_session.cascade_streak = new_streak
    chain_session.current_round += 1

    completed = chain_session.current_round > TOTAL_ROUNDS
    if completed:
        chain_session.game_status = GameStatus.ENDED

    game_repository.save_game_state(session, chain_session)
    game_repository.append_turn(
        session,
        game_id,
        round_played,
        word,
        agent_result.ai_word,
        score_delta,
        breakdown.model_dump(),
    )
    if completed:
        stats_service.record_game_finished(
            session,
            chain_session.username,
            chain_session.difficulty,
            chain_session.total_score,
            completed=True,
        )

    return TurnResponse(
        accepted=True,
        score_delta=score_delta,
        score_breakdown=breakdown,
        ai_move=agent_result.ai_word,
        game_status=chain_session.game_status,
        round=round_played,
    )


def quit_game(session, game_id: str) -> QuitResponse:
    chain_session = game_repository.get_game(session, game_id)
    if chain_session is None:
        raise GameNotFoundError(f"no such game: {game_id}")

    if chain_session.game_status != GameStatus.IN_PROGRESS:
        return QuitResponse(
            game_status=chain_session.game_status, final_score=chain_session.total_score
        )

    chain_session.game_status = GameStatus.QUIT
    game_repository.save_game_state(session, chain_session)
    stats_service.record_game_finished(
        session,
        chain_session.username,
        chain_session.difficulty,
        chain_session.total_score,
        completed=False,
    )
    return QuitResponse(
        game_status=GameStatus.QUIT, final_score=chain_session.total_score
    )
