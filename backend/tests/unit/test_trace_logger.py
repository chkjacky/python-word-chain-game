import json

from app.trace.trace_logger import TraceLogger


def test_log_step_writes_one_well_formed_jsonl_line(tmp_path):
    log_path = tmp_path / "traces.jsonl"
    logger = TraceLogger(str(log_path))

    record = logger.log_step(
        game_id="g1",
        round=1,
        step="validate_word",
        latency_ms=12,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        outcome="valid",
    )

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1

    parsed = json.loads(lines[0])
    assert parsed == record

    required_keys = {
        "step",
        "latency_ms",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "outcome",
    }
    assert required_keys.issubset(parsed.keys())

    assert parsed["game_id"] == "g1"
    assert parsed["round"] == 1
    assert parsed["step"] == "validate_word"
    assert parsed["latency_ms"] == 12
    assert parsed["tokens_in"] == 0
    assert parsed["tokens_out"] == 0
    assert parsed["cost_usd"] == 0.0
    assert parsed["outcome"] == "valid"


def test_log_step_defaults_missing_fields(tmp_path):
    log_path = tmp_path / "traces.jsonl"
    logger = TraceLogger(str(log_path))

    record = logger.log_step(game_id="g1", round=1, step="judge_creativity")

    assert record["latency_ms"] == 0
    assert record["tokens_in"] == 0
    assert record["tokens_out"] == 0
    assert record["cost_usd"] == 0.0
    assert record["outcome"] is None


def test_log_step_appends_without_overwriting(tmp_path):
    log_path = tmp_path / "traces.jsonl"
    logger = TraceLogger(str(log_path))

    logger.log_step(game_id="g1", round=1, step="validate_word", outcome="valid")
    logger.log_step(
        game_id="g1", round=1, step="judge_creativity", outcome="creative=true"
    )

    lines = log_path.read_text().splitlines()
    assert len(lines) == 2


def test_log_step_creates_parent_directories(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "traces.jsonl"
    logger = TraceLogger(str(log_path))

    logger.log_step(game_id="g1", round=1, step="validate_word", outcome="valid")

    assert log_path.exists()
