import litellm
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings

APP_NAME = "word_chain"

RETRYABLE_LLM_ERRORS = (
    litellm.RateLimitError,
    litellm.InternalServerError,
    litellm.ServiceUnavailableError,
    litellm.BadGatewayError,
    litellm.APIConnectionError,
    litellm.Timeout,
)


def build_llm_agent(
    name: str, instruction: str, output_schema: type[BaseModel]
) -> Agent:
    return Agent(
        name=name,
        model=LiteLlm(model=f"openai/{settings.OPENAI_MODEL}"),
        instruction=instruction,
        output_schema=output_schema,
    )


def build_runner(agent: Agent) -> tuple[Runner, InMemorySessionService]:
    session_service = InMemorySessionService()
    return Runner(
        agent=agent, app_name=APP_NAME, session_service=session_service
    ), session_service


async def run_once(
    runner: Runner, session_service: InMemorySessionService, prompt: str
) -> tuple[str, int, int]:
    session = await session_service.create_session(app_name=APP_NAME, user_id="system")
    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    final_text = None
    tokens_in = tokens_out = 0
    async for event in runner.run_async(
        user_id="system", session_id=session.id, new_message=content
    ):
        usage = getattr(event, "usage_metadata", None)
        if usage is not None:
            tokens_in = getattr(usage, "prompt_token_count", None) or tokens_in
            tokens_out = getattr(usage, "candidates_token_count", None) or tokens_out
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts if p.text)
    if not final_text:
        raise ValueError("empty response from agent")
    return final_text, tokens_in, tokens_out
