from app.models.chain_session import ChainSession
from app.models.enums import Difficulty, GameStatus

SAMPLE_CHAIN_SESSION = {
    "game_id": "gm_8f3a1c",
    "username": "jacky",
    "difficulty": "medium",
    "current_round": 4,
    "total_score": 37,
    "used_words": ["dragon", "nectar", "radio", "oxygen"],
    "last_letter": "n",
    "cascade_streak": 2,
    "game_status": "in_progress",
    "retry_counters": {
        "no_s_retry": 0,
        "json_parse_retry": 1,
        "tool_timeout_retry": 0,
    },
    "turn_trace": [
        {
            "step": "validate_word",
            "input": {"word": "oxygen", "last_letter": "i"},
            "tool_calls": [
                {"tool": "dictionary_api", "latency_ms": 212, "outcome": "found"},
                {"tool": "wordfreq_lookup", "latency_ms": 3, "outcome": "zipf=4.1"},
            ],
            "model": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 215,
            "cost_usd": 0.0,
            "outcome": "valid",
        },
        {
            "step": "generate_ai_move",
            "model": "gpt-5-mini",
            "tokens_in": 410,
            "tokens_out": 19,
            "latency_ms": 390,
            "cost_usd": 0.00008,
            "retries": 0,
            "outcome": "word=negotiate",
        },
    ],
}


def test_chain_session_round_trips_sample_json():
    session = ChainSession.model_validate(SAMPLE_CHAIN_SESSION)

    assert session.game_id == "gm_8f3a1c"
    assert session.username == "jacky"
    assert session.difficulty == Difficulty.MEDIUM
    assert session.current_round == 4
    assert session.total_score == 37
    assert session.used_words == ["dragon", "nectar", "radio", "oxygen"]
    assert session.last_letter == "n"
    assert session.cascade_streak == 2
    assert session.game_status == GameStatus.IN_PROGRESS


def test_chain_session_retry_counters_parsed():
    session = ChainSession.model_validate(SAMPLE_CHAIN_SESSION)

    assert session.retry_counters.no_s_retry == 0
    assert session.retry_counters.json_parse_retry == 1
    assert session.retry_counters.tool_timeout_retry == 0


def test_chain_session_turn_trace_parsed():
    session = ChainSession.model_validate(SAMPLE_CHAIN_SESSION)

    assert len(session.turn_trace) == 2

    validate_entry = session.turn_trace[0]
    assert validate_entry.step == "validate_word"
    assert validate_entry.model is None
    assert validate_entry.latency_ms == 215
    assert validate_entry.outcome == "valid"
    assert validate_entry.tool_calls[0]["tool"] == "dictionary_api"

    generate_entry = session.turn_trace[1]
    assert generate_entry.step == "generate_ai_move"
    assert generate_entry.model == "gpt-5-mini"
    assert generate_entry.retries == 0
    assert generate_entry.outcome == "word=negotiate"


def test_chain_session_defaults_when_optional_fields_omitted():
    session = ChainSession(
        game_id="gm_1",
        username="jacky",
        difficulty=Difficulty.EASY,
        current_round=0,
        total_score=0,
        last_letter="a",
        game_status=GameStatus.IN_PROGRESS,
    )

    assert session.used_words == []
    assert session.cascade_streak == 0
    assert session.retry_counters.no_s_retry == 0
    assert session.turn_trace == []
