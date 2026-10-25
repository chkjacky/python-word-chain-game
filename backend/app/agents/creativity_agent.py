import time

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.agents.adk_runtime import RETRYABLE_LLM_ERRORS, build_llm_agent, build_runner, run_once
from app.core.config import settings
from app.models.chain_session import TraceEntry
from app.trace.trace_logger import trace_logger as default_trace_logger
from app.utils.cost import estimate_cost_usd

CREATIVITY_INSTRUCTION = (
    "You are judging word creativity in a word-chain game. Given the word and the "
    "game's difficulty tier, decide if the word is creative (surprising, thematically "
    "interesting, or clever given the difficulty constraints) versus an obvious, "
    "generic choice."
)


class CreativityJudgement(BaseModel):
    creative: bool
    reason: str


class CreativityJudgeAgent:
    def __init__(self, trace_logger=default_trace_logger):
        self.trace_logger = trace_logger
        self._agent = build_llm_agent("creativity_judge", CREATIVITY_INSTRUCTION, CreativityJudgement)
        self._runner, self._session_service = build_runner(self._agent)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.5),
        retry=retry_if_exception_type(RETRYABLE_LLM_ERRORS),
        reraise=True,
    )
    async def _call_llm(self, word: str, difficulty: str) -> tuple[str, int, int]:
        prompt = f"Word: {word}\nDifficulty: {difficulty}"
        return await run_once(self._runner, self._session_service, prompt)

    async def judge(self, chain_session, word: str) -> CreativityJudgement:
        start = time.monotonic()
        retries = 0
        tool_outage = False
        result = None
        tokens_in = tokens_out = 0

        try:
            text, tokens_in, tokens_out = await self._call_llm(word, chain_session.difficulty.value)
            result = CreativityJudgement.model_validate_json(text)
        except RETRYABLE_LLM_ERRORS:
            tool_outage = True
        except ValidationError:
            retries = 1
            try:
                text, tokens_in, tokens_out = await self._call_llm(word, chain_session.difficulty.value)
                result = CreativityJudgement.model_validate_json(text)
            except (ValidationError, *RETRYABLE_LLM_ERRORS):
                pass

        if result is None:
            result = CreativityJudgement(
                creative=False,
                reason="fallback: judge unavailable" if tool_outage else "fallback: judge response could not be parsed",
            )

        latency_ms = int((time.monotonic() - start) * 1000)
        record = self.trace_logger.log_step(
            chain_session.game_id,
            chain_session.current_round,
            "judge_creativity",
            model=settings.OPENAI_MODEL,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=estimate_cost_usd(settings.OPENAI_MODEL, tokens_in, tokens_out),
            latency_ms=latency_ms,
            outcome=f"creative={result.creative}",
            retries=retries,
        )
        chain_session.turn_trace.append(TraceEntry(**record))
        return result


creativity_judge_agent = CreativityJudgeAgent()
