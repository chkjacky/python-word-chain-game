import asyncio
import json
import statistics
import string
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.errors import ToolUnavailableError  # noqa: E402
from app.models.chain_session import ChainSession, RetryCounters  # noqa: E402
from app.models.enums import Difficulty, GameStatus  # noqa: E402

EVAL_DIR = Path(__file__).parent


def _load(name: str) -> list[dict]:
    return json.loads((EVAL_DIR / name).read_text())


def _percentile(values, pct):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def _dummy_session(difficulty: Difficulty, last_letter: str = "a", used_words=None) -> ChainSession:
    return ChainSession(
        game_id="eval",
        username="eval",
        difficulty=difficulty,
        current_round=1,
        total_score=0,
        used_words=used_words or [],
        last_letter=last_letter,
        cascade_streak=0,
        game_status=GameStatus.IN_PROGRESS,
        retry_counters=RetryCounters(),
    )


def run_validation_accuracy(cases: list[dict]) -> dict:
    from app.agents.validator_agent import validate_word

    details = []
    for case in cases:
        difficulty = Difficulty(case["difficulty"])

        if case["dict_mode"] == "found":
            mock_word_exists = lambda word: True  # noqa: E731
        elif case["dict_mode"] == "not_found":
            mock_word_exists = lambda word: False  # noqa: E731
        else:

            def mock_word_exists(word):
                raise ToolUnavailableError("simulated dictionary outage")

        with patch("app.agents.validator_agent.dictionary_client.word_exists", mock_word_exists):
            result = validate_word(case["word"], case["last_letter"], case["used_words"], difficulty)

        passed = result.valid == case["expected_valid"] and (
            case["expected_reason"] is None or result.reason == case["expected_reason"]
        )
        details.append(
            {
                "name": case["name"],
                "expected_valid": case["expected_valid"],
                "expected_reason": case["expected_reason"],
                "actual_valid": result.valid,
                "actual_reason": result.reason,
                "passed": passed,
            }
        )

    accuracy = sum(d["passed"] for d in details) / len(details)
    return {
        "dimension": "validation_accuracy",
        "cases": len(details),
        "accuracy": accuracy,
        "passed": accuracy == 1.0,
        "details": details,
    }


async def run_creativity_calibration(golden_set: list[dict]) -> dict:
    if not settings.OPENAI_API_KEY:
        return {"dimension": "creativity_calibration", "skipped": True, "reason": "no OPENAI_API_KEY configured"}

    from app.agents.creativity_agent import creativity_judge_agent

    details = []
    trace_records = []
    for entry in golden_set:
        difficulty = Difficulty(entry["difficulty"])
        session = _dummy_session(difficulty)
        judgement = await creativity_judge_agent.judge(session, entry["word"])
        trace_records.extend(session.turn_trace)
        details.append(
            {
                "word": entry["word"],
                "difficulty": entry["difficulty"],
                "human_label": entry["creative"],
                "model_label": judgement.creative,
                "agree": judgement.creative == entry["creative"],
            }
        )

    tp = sum(1 for d in details if d["human_label"] and d["model_label"])
    fp = sum(1 for d in details if not d["human_label"] and d["model_label"])
    fn = sum(1 for d in details if d["human_label"] and not d["model_label"])
    tn = sum(1 for d in details if not d["human_label"] and not d["model_label"])

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    agreement = (tp + tn) / len(details)

    return {
        "dimension": "creativity_calibration",
        "cases": len(details),
        "precision": precision,
        "recall": recall,
        "agreement": agreement,
        "passed": agreement >= 0.6,
        "details": details,
        "_trace_records": [r.model_dump() for r in trace_records],
    }


async def run_hard_mode_no_s_compliance(n: int = 30) -> dict:
    if not settings.OPENAI_API_KEY:
        return {"dimension": "hard_mode_no_s_compliance", "skipped": True, "reason": "no OPENAI_API_KEY configured"}

    from app.agents.move_generator_agent import move_generator_agent

    letters = string.ascii_lowercase
    details = []
    trace_records = []
    for i in range(n):
        last_letter = letters[i % len(letters)]
        session = _dummy_session(Difficulty.HARD, last_letter=last_letter)
        word = await move_generator_agent.generate_move(session)
        trace_records.extend(session.turn_trace)
        retries = session.turn_trace[-1].retries if session.turn_trace else None
        details.append(
            {
                "last_letter": last_letter,
                "word": word,
                "ends_in_s": word.endswith("s"),
                "retries": retries,
            }
        )

    s_ending_rate = sum(1 for d in details if d["ends_in_s"]) / len(details)
    retries_seen = [d["retries"] for d in details if d["retries"] is not None]

    return {
        "dimension": "hard_mode_no_s_compliance",
        "generations": len(details),
        "s_ending_rate": s_ending_rate,
        "average_retries": statistics.mean(retries_seen) if retries_seen else None,
        "passed": s_ending_rate == 0.0,
        "details": details,
        "_trace_records": [r.model_dump() for r in trace_records],
    }


def run_adversarial_robustness() -> dict:
    from litellm.types.utils import Choices, Message, ModelResponse
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.agents.creativity_agent import creativity_judge_agent
    from app.agents.move_generator_agent import move_generator_agent
    from app.api.deps import get_db
    from app.main import app
    from app.models.orm import Base

    def fake_response(content: str) -> ModelResponse:
        return ModelResponse(
            id="chatcmpl-eval",
            choices=[Choices(index=0, message=Message(role="assistant", content=content), finish_reason="stop")],
            model=settings.OPENAI_MODEL,
        )

    import tempfile

    tmp_dir = tempfile.mkdtemp()
    engine = create_engine(f"sqlite:///{tmp_dir}/eval.db")
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    cases = [
        ("empty_string", ""),
        ("whitespace_only", "   "),
        ("unicode_emoji", "🔥日本語"),
        ("two_hundred_chars", "a" * 200),
        ("sql_injection_looking", "'; DROP TABLE games; --"),
    ]
    details = []

    try:
        with patch("app.agents.validator_agent.dictionary_client.word_exists", lambda word: True):
            with patch.object(
                move_generator_agent._agent.model.llm_client, "acompletion", AsyncMock(return_value=fake_response('{"word": "dragon"}'))
            ):
                with TestClient(app) as client:
                    start = client.post("/game/start", json={"username": "eval_adversarial", "difficulty": "medium"})
                    game_id = start.json()["game_id"]

                    for name, word in cases:
                        response = client.post(f"/game/{game_id}/turn", json={"word": word})
                        body = response.json() if response.status_code != 500 else None
                        details.append(
                            {
                                "name": name,
                                "status_code": response.status_code,
                                "reason": body.get("reason") if body else None,
                                "crashed": response.status_code == 500,
                                "passed": response.status_code != 500,
                            }
                        )
                        if body and not body.get("accepted", True) and body.get("game_status") == "ended":
                            start = client.post(
                                "/game/start", json={"username": "eval_adversarial", "difficulty": "medium"}
                            )
                            game_id = start.json()["game_id"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    return {
        "dimension": "adversarial_robustness",
        "cases": len(details),
        "passed": all(d["passed"] for d in details),
        "details": details,
    }


def _trace_performance_summary(dimensions: list[dict]) -> dict:
    all_latencies = []
    all_costs = []
    for dim in dimensions:
        for record in dim.get("_trace_records", []):
            if record.get("latency_ms") is not None:
                all_latencies.append(record["latency_ms"])
            if record.get("cost_usd") is not None:
                all_costs.append(record["cost_usd"])
    return {
        "note": (
            "Latency/cost observed during eval dimensions 2 & 3 only, not a full-game benchmark. "
            "See backend/scripts/measure_games.py (Step 12) for p50/p95 full-turn latency and "
            "cost-per-game-per-difficulty."
        ),
        "p50_latency_ms": _percentile(all_latencies, 50),
        "p95_latency_ms": _percentile(all_latencies, 95),
        "avg_cost_usd": statistics.mean(all_costs) if all_costs else None,
        "samples": len(all_latencies),
    }


def _render_markdown(report: dict) -> str:
    lines = ["# Eval Report", ""]
    for key, dim in report.items():
        if key == "performance":
            continue
        lines.append(f"## {dim.get('dimension', key)}")
        if dim.get("skipped"):
            lines.append(f"- SKIPPED: {dim['reason']}")
        else:
            lines.append(f"- passed: {dim.get('passed')}")
            for k, v in dim.items():
                if k in ("dimension", "passed", "details", "_trace_records"):
                    continue
                lines.append(f"- {k}: {v}")
        lines.append("")
    perf = report.get("performance", {})
    lines.append("## performance")
    for k, v in perf.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


async def main():
    validation = run_validation_accuracy(_load("validation_cases.json"))
    adversarial = run_adversarial_robustness()
    creativity = await run_creativity_calibration(_load("creativity_golden_set.json"))
    hard_mode = await run_hard_mode_no_s_compliance()

    report = {
        "validation_accuracy": validation,
        "creativity_calibration": creativity,
        "hard_mode_no_s_compliance": hard_mode,
        "adversarial_robustness": adversarial,
    }
    report["performance"] = _trace_performance_summary([creativity, hard_mode])

    (EVAL_DIR / "eval_report.json").write_text(json.dumps(report, indent=2))
    markdown = _render_markdown(report)
    (EVAL_DIR / "eval_report.md").write_text(markdown)
    print(markdown)


if __name__ == "__main__":
    asyncio.run(main())
