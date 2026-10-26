import asyncio

from pydantic import BaseModel

from app.agents.creativity_agent import creativity_judge_agent
from app.agents.move_generator_agent import move_generator_agent
from app.agents.validator_agent import validator_agent
from app.models.chain_session import ChainSession


class TurnAgentResult(BaseModel):
    valid: bool
    reason: str | None = None
    creative: bool | None = None
    creativity_reason: str | None = None
    ai_word: str | None = None


async def run_turn(chain_session: ChainSession, word: str) -> TurnAgentResult:
    validation = validator_agent.run(chain_session, word)
    if not validation.valid:
        return TurnAgentResult(valid=False, reason=validation.reason)

    projected_session = chain_session.model_copy(
        update={
            "last_letter": word[-1],
            "used_words": chain_session.used_words + [word],
        }
    )

    judgement, ai_word = await asyncio.gather(
        creativity_judge_agent.judge(chain_session, word),
        move_generator_agent.generate_move(projected_session),
    )

    return TurnAgentResult(
        valid=True,
        creative=judgement.creative,
        creativity_reason=judgement.reason,
        ai_word=ai_word,
    )
