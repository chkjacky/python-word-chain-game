from unittest.mock import AsyncMock

import pytest
from litellm.types.utils import Choices, Message, ModelResponse
from pydantic import BaseModel

from app.agents.adk_runtime import build_llm_agent, build_runner, run_once


class _EchoSchema(BaseModel):
    x: int


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


async def test_run_once_returns_final_text_from_mocked_llm():
    agent = build_llm_agent("echo_test", "echo the input as json", _EchoSchema)
    agent.model.llm_client.acompletion = AsyncMock(
        return_value=_fake_response('{"x": 1}')
    )

    runner, session_service = build_runner(agent)
    text, tokens_in, tokens_out = await run_once(runner, session_service, "hello")

    assert text == '{"x": 1}'
    assert tokens_in == 0
    assert tokens_out == 0


async def test_run_once_raises_on_empty_response():
    agent = build_llm_agent("echo_test_empty", "echo the input as json", _EchoSchema)
    agent.model.llm_client.acompletion = AsyncMock(return_value=_fake_response(""))

    runner, session_service = build_runner(agent)

    with pytest.raises(ValueError):
        await run_once(runner, session_service, "hello")
