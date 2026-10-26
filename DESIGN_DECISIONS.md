# Design Decisions

## Why Google ADK

Required by the brief. Each LLM step (creativity judge, move generator) is a real ADK `LlmAgent` run through ADK's `Runner`, with OpenAI `gpt-5-mini` plugged in via ADK's `LiteLlm` wrapper. ADK's `InMemorySessionService` is only the runner's per-call plumbing. It is not the durable store; SQLite is.

The steps are wired together in a plain async function (`agents/orchestrator.py`), not `SequentialAgent`. In `google-adk==2.13.0`, `SequentialAgent` is deprecated and ignores `escalate`, so it can't stop early on an invalid word. A Python `if` can, and it skips both LLM calls when validation fails.

## Agent Steps

1. **ValidatorAgent** (no LLM): letter, repeat and length checks, then the Free Dictionary API, then a `wordfreq` zipf check for the difficulty tier. If the API is down, it falls back to the local wordlist.
2. **CreativityJudgeAgent** (LLM): returns structured `{creative, reason}`. If the JSON won't parse or the LLM fails, it falls back to `creative=false`.
3. **MoveGeneratorAgent** (LLM): generate -> validate -> retry. On Hard, a word ending in "s" is thrown out and generated again (up to `MAX_NO_S_RETRIES`). If retries run out, it picks from a curated wordlist that has already been filtered to exclude S-endings. Words are never truncated or substituted.

## ChainSession

A single Pydantic model carries the state through every step: `game_id, username, difficulty, current_round, total_score, used_words, last_letter, cascade_streak, game_status, retry_counters, turn_trace`. After each turn it is saved to the `games` table. Each trace entry is written to `turn_traces` and to `traces.jsonl`.

## Creativity Rubric

A word counts as creative if it is surprising, thematically interesting or clever for its difficulty tier. A generic, obvious choice is not creative.

## Scoring

`10 base -> +5 if creative -> ×2 on subtotal when the creative streak hits 3, 6, 9… -> +1 per letter beyond 5`. This is a pure function (`domain/scoring.py`) and is unit tested.

## Measured Numbers (`backend/scripts/measure_games.py`, 5 full games per difficulty)

| Difficulty | p50 /turn | p95 /turn | Cost per game |
| ---------- | --------- | --------- | ------------- |
| Easy       | 4.45 s    | 5.21 s    | $0.0028       |
| Medium     | 5.49 s    | 7.21 s    | $0.0038       |
| Hard       | 7.53 s    | 8.99 s    | $0.0046       |

**The latency target is missed.** The brief asks for a p50 under 4 s, and none of the tiers reach it. Each turn makes two LLM calls in sequence plus a dictionary HTTP call, and Hard also adds no-S retries. The fix I would try next is running the creativity judge and the move generator in parallel.

## Scope Cuts

1. SQLite instead of Postgres. Moving is a one-line `DATABASE_URL` change.
2. No Alembic migrations. Tables are created with `create_all()` on startup.
3. No auth. `username` is a free-text field.
4. NextJS instead of Nuxt 3, as instructed.

## Retrospective

- The creativity judge is too strict: precision 1.0 but recall 0.18 against the human-labelled set. The prompt needs few-shot examples, or a rarity signal from `wordfreq`.
- Latency should have been profiled earlier. The two LLM calls in sequence are the bottleneck.
- Writing tests per layer as I went (pure logic -> tools -> repositories -> agents -> API) made the resilience work straightforward.
