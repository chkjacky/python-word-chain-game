import time

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.agents.adk_runtime import RETRYABLE_LLM_ERRORS, build_llm_agent, build_runner, run_once
from app.core.config import settings
from app.core.errors import ToolUnavailableError
from app.domain.chain_rules import LENGTH_BANDS, validate_chain_link
from app.domain.wordlists.loader import load_wordlist
from app.models.chain_session import ChainSession, TraceEntry
from app.models.enums import Difficulty
from app.trace.trace_logger import trace_logger as default_trace_logger
from app.utils.cost import estimate_cost_usd

MOVE_GENERATOR_INSTRUCTION = (
    "You are the AI player in a word-chain game. You will be told the required "
    "starting letter, the allowed word length range, and the words already used. "
    "Generate exactly one next word that satisfies every constraint given."
)

MOVE_GENERATOR_PROMPT_TEMPLATE = (
    "Required starting letter: {last_letter}\n"
    "Allowed length: {min_len}-{max_len} letters\n"
    "Words already used: {used_words}\n"
    "{hard_mode_note}"
)


class MoveGeneration(BaseModel):
    word: str


class MoveGeneratorAgent:
    def __init__(self, trace_logger=default_trace_logger):
        self.trace_logger = trace_logger
        self._agent = build_llm_agent("move_generator", MOVE_GENERATOR_INSTRUCTION, MoveGeneration)
        self._runner, self._session_service = build_runner(self._agent)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.5),
        retry=retry_if_exception_type(RETRYABLE_LLM_ERRORS),
        reraise=True,
    )
    async def _call_llm(self, prompt: str) -> tuple[str, int, int]:
        return await run_once(self._runner, self._session_service, prompt)

    async def _attempt_word(self, chain_session: ChainSession, no_s_required: bool) -> tuple[str | None, int, int]:
        min_len, max_len = LENGTH_BANDS[chain_session.difficulty]
        prompt = MOVE_GENERATOR_PROMPT_TEMPLATE.format(
            last_letter=chain_session.last_letter,
            min_len=min_len,
            max_len=max_len,
            used_words=chain_session.used_words,
            hard_mode_note="- Must NOT end in the letter 's'" if no_s_required else "",
        )
        text, tokens_in, tokens_out = await self._call_llm(prompt)

        try:
            move = MoveGeneration.model_validate_json(text)
        except ValidationError:
            return None, tokens_in, tokens_out

        candidate = move.word.strip().lower()
        result = validate_chain_link(
            candidate, chain_session.last_letter, chain_session.used_words, chain_session.difficulty
        )
        if not result.valid:
            return None, tokens_in, tokens_out
        if no_s_required and candidate.endswith("s"):
            return None, tokens_in, tokens_out
        return candidate, tokens_in, tokens_out

    async def generate_move(self, chain_session: ChainSession) -> str:
        start = time.monotonic()
        no_s_required = chain_session.difficulty == Difficulty.HARD
        max_attempts = settings.MAX_NO_S_RETRIES
        word = None
        attempts = 0
        tool_outage = False
        total_tokens_in = total_tokens_out = 0

        for _ in range(max_attempts):
            attempts += 1
            try:
                candidate, tokens_in, tokens_out = await self._attempt_word(chain_session, no_s_required)
            except RETRYABLE_LLM_ERRORS:
                tool_outage = True
                break
            total_tokens_in += tokens_in
            total_tokens_out += tokens_out
            if candidate:
                word = candidate
                break

        used_fallback = word is None
        if used_fallback:
            word = self._fallback_word(chain_session, no_s_required)

        latency_ms = int((time.monotonic() - start) * 1000)
        outcome = f"word={word}"
        if tool_outage:
            outcome += " (fallback: llm unavailable)"
        elif used_fallback:
            outcome += " (fallback: no_s_retries_exhausted)"

        record = self.trace_logger.log_step(
            chain_session.game_id,
            chain_session.current_round,
            "generate_ai_move",
            model=settings.OPENAI_MODEL,
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            cost_usd=estimate_cost_usd(settings.OPENAI_MODEL, total_tokens_in, total_tokens_out),
            latency_ms=latency_ms,
            outcome=outcome,
            retries=attempts - 1,
        )
        chain_session.turn_trace.append(TraceEntry(**record))
        return word

    def _fallback_word(self, chain_session: ChainSession, no_s_required: bool) -> str:
        used = {w.lower() for w in chain_session.used_words}
        candidates = (
            load_wordlist(Difficulty.EASY) + load_wordlist(Difficulty.MEDIUM) + load_wordlist(Difficulty.HARD)
        )
        for candidate in candidates:
            if candidate.lower() in used:
                continue
            result = validate_chain_link(
                candidate, chain_session.last_letter, chain_session.used_words, chain_session.difficulty
            )
            if not result.valid:
                continue
            if no_s_required and candidate.endswith("s"):
                continue
            return candidate
        raise ToolUnavailableError(
            f"no fallback word available for last_letter={chain_session.last_letter!r}, "
            f"difficulty={chain_session.difficulty}"
        )


move_generator_agent = MoveGeneratorAgent()
