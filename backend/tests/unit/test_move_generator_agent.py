from unittest.mock import AsyncMock

import litellm
import pytest
from litellm.types.utils import Choices, Message, ModelResponse

from app.agents.move_generator_agent import MoveGeneratorAgent
from app.core.errors import ToolUnavailableError
from app.models.chain_session import ChainSession
from app.models.enums import Difficulty, GameStatus
from app.trace.trace_logger import TraceLogger


def _fake_response(content: str) -> ModelResponse:
    return ModelResponse(
        id="chatcmpl-test",
        choices=[
            Choices(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
        model="gpt-5-mini",
    )


def _word_response(word: str) -> ModelResponse:
    return _fake_response(f'{{"word": "{word}"}}')


def _sample_chain_session(difficulty=Difficulty.MEDIUM, last_letter="n"):
    return ChainSession(
        game_id="gm_1",
        username="jacky",
        difficulty=difficulty,
        current_round=1,
        total_score=0,
        used_words=[],
        last_letter=last_letter,
        game_status=GameStatus.IN_PROGRESS,
    )


async def test_generate_move_returns_compliant_word_on_first_try(tmp_path):
    agent = MoveGeneratorAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        return_value=_word_response("network")
    )

    word = await agent.generate_move(_sample_chain_session())

    assert word == "network"
    assert agent._agent.model.llm_client.acompletion.call_count == 1


async def test_hard_mode_falls_back_when_every_attempt_ends_in_s(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MAX_NO_S_RETRIES", 3)
    agent = MoveGeneratorAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    # "expenses" fits HARD's 8-12 length band and starts with "e", but ends in "s" every time
    agent._agent.model.llm_client.acompletion = AsyncMock(
        return_value=_word_response("expenses")
    )

    chain_session = _sample_chain_session(difficulty=Difficulty.HARD, last_letter="e")
    word = await agent.generate_move(chain_session)

    assert not word.endswith("s")
    assert word != "expenses"


async def test_hard_mode_succeeds_after_one_non_compliant_attempt(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.MAX_NO_S_RETRIES", 5)
    agent = MoveGeneratorAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        side_effect=[_word_response("expenses"), _word_response("elephant")]
    )

    chain_session = _sample_chain_session(difficulty=Difficulty.HARD, last_letter="e")
    word = await agent.generate_move(chain_session)

    assert word == "elephant"
    assert agent._agent.model.llm_client.acompletion.call_count == 2


async def test_tool_outage_breaks_immediately_to_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MAX_NO_S_RETRIES", 5)
    agent = MoveGeneratorAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        side_effect=litellm.InternalServerError(
            message="down", model="gpt-5-mini", llm_provider="openai"
        )
    )

    word = await agent.generate_move(_sample_chain_session())

    assert word is not None
    # tenacity's own 3-attempt budget inside _call_llm, but generate_move() must not multiply by MAX_NO_S_RETRIES
    assert agent._agent.model.llm_client.acompletion.call_count == 3


async def test_fallback_raises_tool_unavailable_when_no_candidate_matches(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.MAX_NO_S_RETRIES", 2)
    monkeypatch.setattr(
        "app.agents.move_generator_agent.load_wordlist", lambda difficulty: []
    )
    agent = MoveGeneratorAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        return_value=_word_response("xyzzyx")
    )

    with pytest.raises(ToolUnavailableError):
        await agent.generate_move(_sample_chain_session())
