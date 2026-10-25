import json
from pathlib import Path

from app.core.config import settings


class TraceLogger:
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)

    def log_step(self, game_id: str, round: int, step: str, **fields) -> dict:
        record = {
            "game_id": game_id,
            "round": round,
            "step": step,
            "latency_ms": fields.pop("latency_ms", 0),
            "tokens_in": fields.pop("tokens_in", 0),
            "tokens_out": fields.pop("tokens_out", 0),
            "cost_usd": fields.pop("cost_usd", 0.0),
            "outcome": fields.pop("outcome", None),
            **fields,
        }

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")

        return record


trace_logger = TraceLogger(settings.TRACE_LOG_PATH)
