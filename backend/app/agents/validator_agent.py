import time

from google.adk.tools import FunctionTool

from app.core.errors import ToolUnavailableError
from app.domain.chain_rules import ValidationResult, validate_chain_link
from app.models.chain_session import TraceEntry
from app.models.enums import Difficulty
from app.trace.trace_logger import trace_logger as default_trace_logger
from app.utils.dictionary_client import dictionary_client
from app.utils.frequency_lookup import classify_frequency, is_difficulty_compliant

MAX_WORD_INPUT_LENGTH = 50


def validate_word(
    word: str, last_letter: str, used_words: list[str], difficulty: Difficulty
) -> ValidationResult:
    normalized = word.strip()
    if not normalized:
        return ValidationResult(valid=False, reason="empty_input")
    if len(normalized) > MAX_WORD_INPUT_LENGTH:
        return ValidationResult(valid=False, reason="invalid_format")

    chain_result = validate_chain_link(word, last_letter, used_words, difficulty)
    if not chain_result.valid:
        return chain_result

    try:
        exists = dictionary_client.word_exists(word)
    except ToolUnavailableError:
        exists = classify_frequency(word) > 0
    else:
        if not exists:
            # dictionaryapi.dev's 404 isn't fully authoritative for common function words (observed: "every" 404s
            # even though it's an ordinary English word) - double-check against wordfreq before rejecting outright.
            exists = classify_frequency(word) > 0

    if not exists:
        return ValidationResult(valid=False, reason="not_a_real_word")
    if not is_difficulty_compliant(word, difficulty):
        return ValidationResult(valid=False, reason="wrong_difficulty")
    return ValidationResult(valid=True)


validate_word_tool = FunctionTool(validate_word)


class ValidatorAgent:
    def __init__(self, trace_logger=default_trace_logger):
        self.trace_logger = trace_logger

    def run(self, chain_session, word: str) -> ValidationResult:
        start = time.monotonic()
        result = validate_word(
            word,
            chain_session.last_letter,
            chain_session.used_words,
            chain_session.difficulty,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        record = self.trace_logger.log_step(
            chain_session.game_id,
            chain_session.current_round,
            "validate_word",
            latency_ms=latency_ms,
            input={"word": word, "last_letter": chain_session.last_letter},
            outcome="valid" if result.valid else f"invalid:{result.reason}",
        )
        chain_session.turn_trace.append(TraceEntry(**record))
        return result


validator_agent = ValidatorAgent()
