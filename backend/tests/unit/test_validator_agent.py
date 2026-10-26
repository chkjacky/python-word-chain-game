import pytest

from app.agents.validator_agent import ValidatorAgent, validate_word
from app.core.errors import ToolUnavailableError
from app.models.chain_session import ChainSession
from app.models.enums import Difficulty, GameStatus
from app.trace.trace_logger import TraceLogger


def test_validate_word_valid_real_word(monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)

    result = validate_word("nectar", "n", [], Difficulty.MEDIUM)

    assert result.valid is True


def test_validate_word_wrong_letter(monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)

    result = validate_word("radio", "x", [], Difficulty.MEDIUM)

    assert result.valid is False
    assert result.reason == "wrong_letter"


def test_validate_word_repeated(monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)

    result = validate_word("nectar", "n", ["nectar"], Difficulty.MEDIUM)

    assert result.valid is False
    assert result.reason == "repeated_word"


def test_validate_word_wrong_length(monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)

    result = validate_word("ox", "o", [], Difficulty.EASY)

    assert result.valid is False
    assert result.reason == "invalid_length"


def test_validate_word_not_a_real_word(monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: False)

    result = validate_word("zzzqx", "z", [], Difficulty.EASY)

    assert result.valid is False
    assert result.reason == "not_a_real_word"


def test_validate_word_dictionary_404_overridden_by_wordfreq_for_common_word(monkeypatch):
    # dictionaryapi.dev genuinely 404s on ordinary function words like "every" (observed live) - a 404
    # shouldn't be treated as fully authoritative when wordfreq clearly recognizes the word as real.
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: False)

    result = validate_word("every", "e", [], Difficulty.EASY)

    assert result.valid is True


def test_validate_word_wrong_difficulty(monkeypatch):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)

    # "beautiful" fits HARD's 8-12 length band but is too common (high zipf) for HARD's uncommon-word requirement
    result = validate_word("beautiful", "b", [], Difficulty.HARD)

    assert result.valid is False
    assert result.reason == "wrong_difficulty"


def test_validate_word_degrades_to_wordfreq_when_dictionary_tool_down(monkeypatch):
    def _raise(word):
        raise ToolUnavailableError("dictionary down")

    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", _raise)

    result = validate_word("house", "h", [], Difficulty.EASY)

    assert result.valid is True


def test_validate_word_gibberish_rejected_when_dictionary_tool_down(monkeypatch):
    def _raise(word):
        raise ToolUnavailableError("dictionary down")

    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", _raise)

    result = validate_word("zzzqx", "z", [], Difficulty.EASY)

    assert result.valid is False
    assert result.reason == "not_a_real_word"


@pytest.mark.parametrize("word", ["", "   "])
def test_validate_word_empty_or_whitespace_rejected_as_empty_input(word):
    result = validate_word(word, "n", [], Difficulty.MEDIUM)

    assert result.valid is False
    assert result.reason == "empty_input"


def test_validate_word_overlong_input_rejected_as_invalid_format():
    result = validate_word("a" * 200, "a", [], Difficulty.MEDIUM)

    assert result.valid is False
    assert result.reason == "invalid_format"


def test_validator_agent_run_logs_a_trace_line(monkeypatch, tmp_path):
    monkeypatch.setattr("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True)

    log_path = tmp_path / "traces.jsonl"
    agent = ValidatorAgent(trace_logger=TraceLogger(str(log_path)))
    chain_session = ChainSession(
        game_id="gm_1",
        username="jacky",
        difficulty=Difficulty.MEDIUM,
        current_round=1,
        total_score=0,
        used_words=[],
        last_letter="n",
        game_status=GameStatus.IN_PROGRESS,
    )

    result = agent.run(chain_session, "nectar")

    assert result.valid is True
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    assert '"step": "validate_word"' in lines[0]
