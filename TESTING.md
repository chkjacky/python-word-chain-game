# Testing

## Unit + Integration Tests

```bash
cd backend
pytest
```

- `tests/unit/`: scoring, chain rules, dictionary client (mocked httpx), wordfreq lookup, repositories (on a temp SQLite file), each agent step (mocked LLM), orchestrator, services.
- `tests/integration/`:
  - `test_game_api.py`: a full game run through `TestClient`.
  - `test_resilience.py`: malformed LLM JSON, 429/5xx, dictionary outage, and adversarial input (empty, whitespace, unicode, 200 characters). None of these may return a 500.
  - `test_persistence_restart.py`: plays a game, restarts the app on the same DB file, and checks that state, trace and stats are unchanged.

## Eval Harness

```bash
cd backend
.venv/bin/python ../eval/run_eval.py   # writes eval/eval_report.{json,md}
```

Last run:

| Dimension                | Cases | Result                                          |
| ------------------------ | ----- | ----------------------------------------------- |
| Validation accuracy      | 22    | 100% ✅                                          |
| Creativity calibration   | 22    | 59% agreement, precision 1.0, recall 0.18 ❌     |
| Hard-mode no-S (after retry) | 30 | 0% end in S ✅                                  |
| Adversarial robustness   | 5     | all passed ✅                                    |

## Latency / Cost

```bash
# with the backend running (docker compose up, or uvicorn locally)
cd backend
python scripts/measure_games.py --base-url http://localhost:8000 --games-per-difficulty 5
```

This needs the backend running. It writes `backend/measurement_report.json`; the numbers are in `DESIGN_DECISIONS.md`.

## Manual

I played one full game per difficulty in the UI and checked the stats and leaderboard pages and the dev-mode trace panel. Screenshots are in `samples/`.
