# AI Word Chain Game

AI opens with a word, the player replies with a word starting from the last letter, scored and adjudicated by a multi-step Google ADK agent.

## 🩻 Sample Pages

### Homepage

![Homepage](https://raw.githubusercontent.com/chkjacky/python-word-chain-game/refs/heads/main/samples/homepage.png)

### Game Screen

![Game-Screen-Easy](https://github.com/chkjacky/python-word-chain-game/blob/main/samples/game-screen-easy.png?raw=true)
![Game-Screen-Medium](https://github.com/chkjacky/python-word-chain-game/blob/main/samples/game-screen-medium.png?raw=true)
![Game-Screen-Hard](https://github.com/chkjacky/python-word-chain-game/blob/main/samples/game-screen-hard.png?raw=true)

### Statistic Page

![StatPage](https://github.com/chkjacky/python-word-chain-game/blob/main/samples/stat-page.png?raw=true)

### Leaderboard Page

![Leaderboard](https://github.com/chkjacky/python-word-chain-game/blob/main/samples/leaderboard.png?raw=true)

### Trace
![Trace](https://github.com/chkjacky/python-word-chain-game/blob/main/samples/trace.png?raw=true)

## 🎲 Game Rules

**Flow.** The AI opens with a word. You reply with a word starting with the last letter of the previous word. This continues for 10 rounds (AI + player = 1 round each).

**What ends the game.** Only an _invalid_ word ends it immediately - no retries, no partial credit:

- doesn't start with the required last letter
- already used earlier in this game
- wrong length for the chosen difficulty
- not a real word
- wrong difficulty tier (too common for Hard, too obscure for Easy/Medium)

A _valid but uncreative_ word does **not** end the game - it's just worth fewer points and resets your creativity streak (see below).

**Difficulty bands:**

| Difficulty | Length | Word pool  | Extra rule                                                                                        |
| ---------- | ------ | ---------- | ------------------------------------------------------------------------------------------------- |
| Easy       | 4-6    | common     | -                                                                                                 |
| Medium     | 6-8    | well-known | -                                                                                                 |
| Hard       | 8-12   | uncommon   | the AI never produces a word ending in "s" (retries until compliant, never truncates/substitutes) |

**Scoring**, applied in this exact order:

1. **+10** base, for any valid word
2. **+5** if the word is judged creative (rare/surprising for the difficulty band)
3. **×2** on the subtotal, once every 3rd _consecutive_ creative word (3rd, 6th, 9th creative word in a row - breaking the streak with one uncreative word resets the count)
4. **+1 per letter** beyond 5, added last (e.g. a 13-letter word gets +8)

Example: a 13-letter word that's your 3rd consecutive creative word -> `10 -> +5 = 15 -> ×2 = 30 -> +8 length = 38`. The same word as your 2nd consecutive creative word (no cascade) -> `10 -> +5 = 15 -> +8 length = 23`.

## 🔋 Current Status

**Creativity calibration** currently has low recall (0.18) against the held-out set - see `eval/eval_report.md`. Precision is 1.0 (no false positives), but the judge is conservative and misses genuinely creative words more often than it should.

## ⚙️ Tech Stack

- **Backend**: FastAPI, Google ADK (multi-step agent: `ValidatorAgent` -> `CreativityJudgeAgent` -> `MoveGeneratorAgent`), OpenAI `gpt-5-mini` via ADK's `LiteLlm` wrapper
- **Durable store**: SQLite (file-backed, via SQLAlchemy) - games, turns, trace entries, player stats
- **Frontend**: Next.js 16 (App Router), Tailwind v4, shadcn/ui
- **Container**: Docker + Docker Compose

## 🧬 Project Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI app, CORS, GET /health
│   ├── core/                 # config, typed errors + exception handlers
│   ├── trace/                # JSONL trace logger
│   ├── models/               # Pydantic (ChainSession, API shapes) + SQLAlchemy ORM
│   ├── domain/               # pure logic: scoring, chain-link validation, wordlists
│   ├── utils/                # dictionary API client, wordfreq lookup, cost calc
│   ├── repositories/         # game + stats persistence
│   ├── agents/               # the 3 ADK agent steps + orchestrator
│   ├── services/             # game_service, stats_service
│   └── api/routers/          # game.py, stats.py
├── tests/                    # unit + integration
├── scripts/measure_games.py  # latency/cost-per-game measurement
├── requirements.txt
├── .env.example
└── Dockerfile

frontend/
├── app/
│   ├── page.tsx              # start screen
│   ├── game/[id]/page.tsx    # chat-style game screen, dev-mode trace panel
│   ├── stats/[username]/page.tsx
│   ├── leaderboard/page.tsx
│   ├── not-found.tsx, error.tsx, loading.tsx (per route)
├── components/
│   ├── chat/                 # GameTranscript, ScoreChip, CascadeIndicator, ErrorBanner, DevTracePanel
│   └── ui/                   # shadcn primitives
└── lib/                      # types.ts, api-client.ts

eval/
├── run_eval.py               # unattended 4-dimension eval harness
├── validation_cases.json
├── creativity_golden_set.json
└── eval_report.{json,md}     # last run's output

docker-compose.yml
README.md
```

## ⚠️ Prerequisites

- Docker & Docker Compose
- An OpenAI API key
- Python 3.11+ (only needed for local, non-Docker backend dev, or to run the eval/measurement scripts)
- Node 24.22.3+ (only needed for local, non-Docker frontend dev)

## 🏃 Quick start (Docker, recommended)

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set OPENAI_API_KEY

docker compose build
docker compose up -d
# or, build + start in one step, rebuilding images if anything changed:
docker compose up --build
```

Then open:

- `http://localhost:3000` - the game UI
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/health` -> `{"status":"healthy"}`

Note on an easy-to-hit Docker gotcha: `docker-compose.yml` mounts `node_modules`/`.next` as **anonymous volumes** for the frontend. If you rebuild the image after changing `frontend/package.json`, the old anonymous volume can still shadow the freshly-installed `node_modules`. If you see `Module not found` errors after a rebuild, run `docker compose down -v && docker compose up --build` to drop the stale volumes too.

## 🚶 Local Dev (Optional, Without Docker)

**Backend:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Optional for formatting python code with Ruff after pip install
ruff format .
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

`lib/api-client.ts` reads `NEXT_PUBLIC_API_URL`, falling back to `http://localhost:8000` if unset, so `npm run dev` works standalone against a locally-running backend with zero extra config.

## 🏞️ Environment Variables

All backend variables live in `backend/.env.example`, used by both Docker Compose (`env_file`) and local dev:

| Variable           | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| `OPENAI_API_KEY`   | OpenAI API key, used by the LLM-backed agent steps |
| `OPENAI_MODEL`     | Default `gpt-5-mini`                               |
| `DATABASE_URL`     | SQLite connection string                           |
| `TRACE_LOG_PATH`   | Path to the per-turn JSONL trace log               |
| `MAX_LLM_RETRIES`  | Retry budget for LLM 429/5xx                       |
| `MAX_NO_S_RETRIES` | Retry budget for Hard-mode no-S word generation    |

Frontend: `NEXT_PUBLIC_API_URL`, injected by `docker-compose.yml` directly; defaults to `http://localhost:8000` in code otherwise.

## 🔗 API

| Endpoint                | Purpose                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| `POST /game/start`      | Start a game `{username, difficulty}`                               |
| `POST /game/{id}/turn`  | Submit a word, get the AI's reply + score breakdown                 |
| `GET /game/{id}/state`  | Lightweight current state                                           |
| `GET /game/{id}/trace`  | Full ordered per-turn trace (model, tokens, latency, cost, outcome) |
| `POST /game/{id}/quit`  | End the game early                                                  |
| `GET /stats/{username}` | Player stats, zeroed defaults if no games                           |
| `GET /leaderboard`      | Top 10 by best score                                                |
| `GET /health`           | Liveness check                                                      |

Errors use `{"error": {"code", "message"}}` with the matching HTTP status (422/404/503); plain Pydantic validation errors fall back to FastAPI's default `{"detail": [...]}` shape - `frontend/lib/api-client.ts` normalizes both into one `ApiRequestError`.

## 🧪 Running Tests

```bash
cd backend
.venv/bin/pytest                   # full suite (unit + integration)
.venv/bin/pytest tests/unit -v     # unit tests only, verbose
```

Runs against `backend/tests/`; `backend/pytest.ini` sets `pythonpath = .` and `asyncio_mode = auto`, so no extra flags are needed. Calling `.venv/bin/pytest` directly works without activating the venv (if it's already activated, plain `pytest` is equivalent). Create the venv first via Local dev above if you haven't.

## 🥼 Eval Harness

```bash
cd backend
.venv/bin/python ../eval/run_eval.py
```

Runs unattended against the four required dimensions - validation accuracy (22 cases), creativity calibration vs. a held-out human-labelled set (22 cases), Hard-mode no-S compliance (30 generations), and adversarial robustness - and writes `eval/eval_report.json` / `eval/eval_report.md`. Current results are checked in; re-run to refresh them.

## 📏 Measured Performance

```bash
# with the backend running (docker compose up, or uvicorn locally)
cd backend
python scripts/measure_games.py --base-url http://localhost:8000 --games-per-difficulty 5
```

Plays 5 full games per difficulty against the live API and writes `backend/measurement_report.json`. Last measured:

| Difficulty | p50 latency | p95 latency | Avg cost/game |
| ---------- | ----------- | ----------- | ------------- |
| Easy       | 4.45s       | 5.21s       | $0.0028       |
| Medium     | 5.49s       | 7.21s       | $0.0038       |
| Hard       | 7.53s       | 8.99s       | $0.0046       |

(5 games each, 50 turns measured per difficulty.)
