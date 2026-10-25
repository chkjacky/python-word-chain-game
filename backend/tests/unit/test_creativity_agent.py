from unittest.mock import AsyncMock

import litellm
from litellm.types.utils import Choices, Message, ModelResponse

from app.agents.creativity_agent import CreativityJudgeAgent
from app.models.chain_session import ChainSession
from app.models.enums import Difficulty, GameStatus
from app.trace.trace_logger import TraceLogger


def _fake_response(content: str) -> ModelResponse:
    return ModelResponse(
        id="chatcmpl-test",
        choices=[Choices(index=0, message=Message(role="assistant", content=content), finish_reason="stop")],
        model="gpt-5-mini",
    )


def _sample_chain_session():
    return ChainSession(
        game_id="gm_1",
        username="jacky",
        difficulty=Difficulty.MEDIUM,
        current_round=1,
        total_score=0,
        used_words=[],
        last_letter="n",
        game_status=GameStatus.IN_PROGRESS,
    )


async def test_judge_returns_result_on_first_valid_response(tmp_path):
    agent = CreativityJudgeAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        return_value=_fake_response('{"creative": true, "reason": "clever pun"}')
    )

    result = await agent.judge(_sample_chain_session(), "nectar")

    assert result.creative is True
    assert result.reason == "clever pun"


async def test_judge_retries_once_on_malformed_json_then_succeeds(tmp_path):
    agent = CreativityJudgeAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        side_effect=[
            _fake_response("not json at all"),
            _fake_response('{"creative": false, "reason": "obvious choice"}'),
        ]
    )

    result = await agent.judge(_sample_chain_session(), "nectar")

    assert result.creative is False
    assert result.reason == "obvious choice"
    assert agent._agent.model.llm_client.acompletion.call_count == 2


async def test_judge_falls_back_deterministically_after_two_malformed_responses(tmp_path):
    agent = CreativityJudgeAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        side_effect=[_fake_response("not json"), _fake_response("still not json")]
    )

    result = await agent.judge(_sample_chain_session(), "nectar")

    assert result.creative is False
    assert "fallback" in result.reason


async def test_judge_falls_back_immediately_on_tool_outage_without_second_attempt(tmp_path):
    agent = CreativityJudgeAgent(trace_logger=TraceLogger(str(tmp_path / "traces.jsonl")))
    agent._agent.model.llm_client.acompletion = AsyncMock(
        side_effect=litellm.InternalServerError(
            message="down", model="gpt-5-mini", llm_provider="openai"
        )
    )

    result = await agent.judge(_sample_chain_session(), "nectar")

    assert result.creative is False
    assert "fallback" in result.reason
    # tenacity's own 3-attempt budget inside _call_llm, but judge() must not retry a second full cycle on top
    assert agent._agent.model.llm_client.acompletion.call_count == 3
