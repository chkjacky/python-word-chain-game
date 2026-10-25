import argparse
import json
import statistics
import time
import uuid

import httpx
from wordfreq import top_n_list

from app.domain.chain_rules import validate_chain_link
from app.models.enums import Difficulty
from app.utils.frequency_lookup import is_difficulty_compliant

DIFFICULTIES = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]


def _build_candidate_pool(n: int = 100_000) -> list[str]:
    return top_n_list("en", n)


def _pick_next_word(pool, last_letter, used_words, difficulty) -> str | None:
    used_lower = {w.lower() for w in used_words}
    for candidate in pool:
        candidate = candidate.lower()
        if candidate in used_lower:
            continue
        if not validate_chain_link(candidate, last_letter, used_words, difficulty).valid:
            continue
        if not is_difficulty_compliant(candidate, difficulty):
            continue
        return candidate
    return None


def play_one_game(client, base_url, username, difficulty, pool) -> dict:
    start = client.post(f"{base_url}/game/start", json={"username": username, "difficulty": difficulty.value})
    start.raise_for_status()
    start_body = start.json()
    snapshot = start_body["chain_session_snapshot"]
    game_id = start_body["game_id"]
    used_words = list(snapshot["used_words"])
    last_letter = snapshot["last_letter"]

    turn_latencies_ms = []
    rounds_completed = 0
    for _ in range(10):
        word = _pick_next_word(pool, last_letter, used_words, difficulty)
        if word is None:
            break
        used_words.append(word)

        t0 = time.monotonic()
        response = client.post(f"{base_url}/game/{game_id}/turn", json={"word": word})
        turn_latencies_ms.append((time.monotonic() - t0) * 1000)
        response.raise_for_status()
        body = response.json()

        if not body["accepted"]:
            break
        rounds_completed += 1
        used_words.append(body["ai_move"])
        last_letter = body["ai_move"][-1]

    trace = client.get(f"{base_url}/game/{game_id}/trace")
    trace.raise_for_status()
    cost_usd = sum(e.get("cost_usd", 0.0) for e in trace.json()["trace"])
    client.post(f"{base_url}/game/{game_id}/quit")

    return {
        "difficulty": difficulty.value,
        "rounds_completed": rounds_completed,
        "full_game": rounds_completed == 10,
        "turn_latencies_ms": turn_latencies_ms,
        "cost_usd": cost_usd,
    }


def _percentile(values, pct):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100)
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--games-per-difficulty", type=int, default=5)
    args = parser.parse_args()

    pool = _build_candidate_pool()
    report = {}
    with httpx.Client(timeout=30.0) as client:
        for difficulty in DIFFICULTIES:
            games = [
                play_one_game(
                    client, args.base_url, f"measure_{difficulty.value}_{uuid.uuid4().hex[:6]}", difficulty, pool
                )
                for _ in range(args.games_per_difficulty)
            ]
            all_latencies = [lat for g in games for lat in g["turn_latencies_ms"]]
            costs = [g["cost_usd"] for g in games]
            report[difficulty.value] = {
                "games_played": len(games),
                "games_completed_full_10_rounds": sum(1 for g in games if g["full_game"]),
                "p50_latency_ms": _percentile(all_latencies, 50),
                "p95_latency_ms": _percentile(all_latencies, 95),
                "avg_cost_usd_per_game": statistics.mean(costs) if costs else None,
                "turns_measured": len(all_latencies),
            }

    print(json.dumps(report, indent=2))
    with open("measurement_report.json", "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
