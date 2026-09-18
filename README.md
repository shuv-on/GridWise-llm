# GridWise — Smart Campus Energy Optimization API

**BUP CSE Fest 2026 · Hackathon · Online Preliminary**

LLM-assisted operator directive interpretation + 24-hour energy cost optimization.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Architecture](#architecture)
3. [Quick Start (5 minutes)](#quick-start-5-minutes)
4. [Environment Variables](#environment-variables)
5. [Running the Service](#running-the-service)
6. [API Reference](#api-reference)
7. [Testing](#testing)
8. [Docker](#docker)
9. [Project Structure](#project-structure)
10. [How It Works Internally](#how-it-works-internally)
11. [Troubleshooting](#troubleshooting)
12. [Known Limitations](#known-limitations)

---

## What This Project Does

GridWise receives a 24-hour energy scenario (demand, solar, tariff, battery state) plus 1–3 natural-language operator notes. It:

1. Uses an **LLM** to interpret each note into a structured directive
2. **Validates** the LLM output with deterministic guardrails
3. **Optimizes** a 24-hour schedule (LP solver) that respects all directives and minimizes grid electricity cost
4. Returns both the interpretation and the final hourly plan as JSON

**Supported directive types:**
- `solar_reduction` — usable solar reduced by a factor during specific hours
- `minimum_battery_reserve` — battery must stay at or above a level
- `no_charge_window` — battery charging disabled during hours
- `no_discharge_window` — battery discharging disabled during hours
- `max_grid_window` — grid import capped during hours
- `no_op` — irrelevant note (ignored)

---

## Architecture

```
┌─────────────────┐
│  Client (POST)  │
└────────┬────────┘
         │  JSON: { scenario_id, operator_notes, hours, battery }
         ▼
┌─────────────────────────────────────────────┐
│  FastAPI  ·  POST /optimize-energy          │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────┐
│  LLM Cache      │───▶│  Cache Hit?  │───yes──▶┐
└─────────────────┘    └──────┬───────┘         │
                              │ no              │
                              ▼                 │
                     ┌─────────────────┐        │
                     │  LLM Interpreter│        │
                     │  (Groq/OpenAI)  │        │
                     └────────┬────────┘        │
                              │                  │
                              ▼                  │
                     ┌─────────────────┐        │
                     │  Guardrail      │        │
                     │  Validator      │        │
                     └────────┬────────┘        │
                              │                  │
                              ▼                  ▼
                     ┌──────────────────────────┐
                     │  Directive Set           │
                     └────────┬─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  PuLP LP Solver │
                     │  (24-hour plan) │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Final Response │
                     └─────────────────┘
```

**Pipeline stages:**

| Stage | Purpose |
|---|---|
| **LLM Interpreter** | Converts natural-language notes to structured directives |
| **Guardrail Validator** | Rejects malformed/hallucinated LLM output |
| **Cache** | Avoids repeat LLM calls for identical notes |
| **Optimizer** | PuLP CBC solver minimizes total grid cost |
| **Response** | Returns interpretation + 24-hour plan |

---

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **pip** and **venv**
- **curl** (for testing)
- A valid **LLM API key** (Groq / OpenAI / Gemini)

### Step 1 — Clone or navigate to project

```bash
cd /path/to/gridwise
```

### Step 2 — Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Ubuntu, if `python3-venv` is missing:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
```

### Step 3 — Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in **at minimum**:

```env
LLM_PROVIDER=groq
LLM_API_KEY=your-real-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

> **Never commit `.env` to git.** It's already in `.gitignore`.

### Step 5 — Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6 — Verify

Open a second terminal:

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Interactive docs
# Open in browser: http://localhost:8000/docs
```

---

## Environment Variables

All variables are read from `.env`. See `.env.example` for the full list.

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_NAME` | No | `GridWise` | App display name |
| `APP_ENV` | No | `development` | `development` / `staging` / `production` |
| `APP_HOST` | No | `0.0.0.0` | Bind host |
| `APP_PORT` | No | `8000` | Bind port |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LLM_PROVIDER` | **Yes** | `openai` | `openai` / `groq` / `gemini` / `openai_compatible` |
| `LLM_API_KEY` | **Yes** | — | Provider API key |
| `LLM_BASE_URL` | **Yes** | OpenAI URL | Provider base URL |
| `LLM_MODEL` | **Yes** | `gpt-4o-mini` | Model identifier |
| `LLM_TIMEOUT_SECONDS` | No | `20` | Per-call timeout |
| `LLM_MAX_RETRIES` | No | `2` | Retry attempts |
| `LLM_TEMPERATURE` | No | `0.0` | Sampling temperature |
| `OPTIMIZER_TIME_LIMIT_SECONDS` | No | `10` | PuLP solver time limit |

### Recommended providers

| Provider | Base URL | Model | Notes |
|---|---|---|---|
| **Groq** | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` | Fast, free tier available |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini` | Paid, most reliable |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-1.5-flash` | Free tier available |

---

## Running the Service

### Development (with auto-reload)

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production-style (Gunicorn)

```bash
gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60
```

### Quick helpers

```bash
# Using Makefile
make install     # install dependencies
make run         # start dev server
make test        # run pytest
make smoke       # run smoke test
make docker      # build docker image

# Using run.sh
./run.sh
```

---

## API Reference

### `GET /health`

Readiness probe.

**Response** `200 OK`:
```json
{"status": "ok"}
```

---

### `POST /optimize-energy`

Main endpoint.

**Request** (`Content-Type: application/json`):

```json
{
  "scenario_id": "TEST-01",
  "operator_notes": [
    "Solar output will drop to about 20% from 1 PM to 3 PM.",
    "The cafeteria menu changes tomorrow."
  ],
  "hours": [
    {"hour": 0, "demand_kwh": 100, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
    {"hour": 1, "demand_kwh": 95, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
    ... 22 more entries ...
  ],
  "battery": {
    "capacity_kwh": 220,
    "initial_energy_kwh": 110,
    "minimum_energy_kwh": 40,
    "max_charge_kwh_per_hour": 50,
    "max_discharge_kwh_per_hour": 50
  }
}
```

**Required fields:**

| Field | Type | Notes |
|---|---|---|
| `scenario_id` | string | Any non-empty identifier |
| `operator_notes` | array[1..3] of string | Non-empty strings |
| `hours` | array[24] | Exactly 24 entries for hours 0..23 |
| `battery` | object | See battery fields below |

**Battery object:**

| Field | Type |
|---|---|
| `capacity_kwh` | float > 0 |
| `initial_energy_kwh` | float ≥ 0 |
| `minimum_energy_kwh` | float ≥ 0 |
| `max_charge_kwh_per_hour` | float > 0 |
| `max_discharge_kwh_per_hour` | float > 0 |

**Response** `200 OK`:

```json
{
  "scenario_id": "TEST-01",
  "directive_interpretation": [
    {
      "note_index": 0,
      "applies": true,
      "directive_type": "solar_reduction",
      "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
      "explanation": "Solar reduced to 20% during 1-3 PM"
    },
    {
      "note_index": 1,
      "applies": false,
      "directive_type": "no_op",
      "structured_adjustment": null,
      "explanation": "Irrelevant to energy scheduling"
    }
  ],
  "hourly_plan": [
    {
      "hour": 0,
      "grid_kwh": 100,
      "solar_used_kwh": 0,
      "battery_action": "idle",
      "battery_kwh": 0,
      "battery_energy_after_kwh": 110
    },
    ... 23 more entries ...
  ],
  "total_grid_kwh": 2703.0,
  "total_cost_bdt": 37108.0,
  "peak_grid_kwh": 187.0,
  "plan_summary": "Applied 1 directive(s): solar_reduction..."
}
```

**Response status codes:**

| Code | Meaning |
|---|---|
| `200` | Success |
| `400` | Malformed JSON or invalid request |
| `422` | LLM output failed guardrails |
| `500` | Internal error |
| `503` | LLM provider rate-limited (retry with `Retry-After` header) |

---

## Testing

### Run unit tests

```bash
source .venv/bin/activate
pytest -v
```

### With coverage

```bash
pytest --cov=app --cov-report=term-missing
```

### Smoke test (end-to-end)

Make sure the server is running first, then:

```bash
bash scripts/smoke_test.sh
```

Or:

```bash
make smoke
```

### Run all 10 public sample cases

```bash
python3 scripts/run_public_samples.py
```

This validates:

- All 10 cases return `200 OK`
- Each response has 24 hourly entries
- Battery, energy balance, end-of-day neutrality all hold
- Directive interpretations match ground truth

---

## Docker

### Build the image

```bash
docker build -t gridwise:latest .
```

### Run the container

```bash
docker run --rm -p 8000:8000 \
  --env-file .env \
  gridwise:latest
```

### Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Docker Compose

```bash
docker compose up --build
```

### Docker fallback (for organizers)

Image reference for judging:

```
docker pull <your-registry>/gridwise:<tag>
docker run --rm -p 8000:8000 --env-file .env <your-registry>/gridwise:<tag>
```

**Image requirements:**

- Binds to `0.0.0.0:8000`
- Reads env vars from `.env` at runtime
- **No secrets baked into the image**

---

## Project Structure

```
gridwise/
├── app/
│   ├── main.py                    # FastAPI app entrypoint
│   ├── config.py                  # Settings from .env
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── health.py          # GET /health
│   │       └── optimize.py        # POST /optimize-energy
│   ├── schemas/
│   │   ├── request.py             # Request models
│   │   ├── response.py            # Response models
│   │   └── directives.py          # Directive enums/types
│   ├── services/
│   │   ├── llm/
│   │   │   ├── base.py            # LLM interface
│   │   │   ├── openai_client.py   # OpenAI-compatible client
│   │   │   ├── prompts.py         # Prompt templates
│   │   │   └── cache.py           # LLM response cache
│   │   ├── guardrails/
│   │   │   └── validator.py       # Deterministic validation
│   │   └── optimizer/
│   │       ├── energy_model.py    # Directive set model
│   │       └── solver.py          # PuLP LP solver
│   ├── core/
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── logging.py             # Structured logging
│   └── utils/
│       └── time_utils.py          # Hour parsing helpers
├── tests/                         # pytest suite
├── scripts/
│   ├── smoke_test.sh              # End-to-end test
│   └── run_public_samples.py      # Sample validator
├── data/
│   └── public_samples.json        # 10 public cases
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## How It Works Internally

### 1. Request arrives

FastAPI validates the request using Pydantic schemas in `app/schemas/request.py`. Invalid requests are rejected with `422`.

### 2. Cache lookup

Cache key = `sha256(normalized_notes + battery_capacity)`. If hit, skip LLM. Otherwise, proceed.

### 3. LLM interpretation

`app/services/llm/openai_client.py` calls the provider with a **strict JSON-only system prompt** (`app/services/llm/prompts.py`) that:

- Enumerates all directive types and their exact `structured_adjustment` shapes
- Explains time rules (start-inclusive, end-exclusive)
- Explains percentage normalization (`80% reduction` → `factor = 0.2`)
- Requires exactly one entry per note, in `note_index` order

Response is parsed as JSON. Failure → `LLMError`.

### 4. Guardrail validation

`app/services/guardrails/validator.py` re-validates every field:

- `directive_type` ∈ allowed set
- `hours` unique ints 0-23, ascending
- `factor` ∈ [0, 1]
- `minimum_energy_kwh`, `max_grid_kwh` ≥ 0
- `no_op` → `applies = false`, `structured_adjustment = null`
- Every other type → `applies = true`, adjustment present
- `note_index` matches position

Any violation → `GuardrailError` → `422`.

### 5. Optimization

`app/services/optimizer/solver.py` builds a linear program with PuLP:

**Variables (per hour h):**
- `grid[h]` ≥ 0
- `solar_used[h]` ∈ [0, effective_solar[h]]
- `charge[h]` ≥ 0
- `discharge[h]` ≥ 0
- `e_after[h]` ∈ [min_energy[h], capacity]

**Objective:** minimize `Σ grid[h] × tariff[h]`

**Constraints:**
- Energy balance: `grid + solar_used + discharge = demand + charge`
- Battery transition: `e_after[h] = e_after[h-1] + charge[h] - discharge[h]`
- Rate limits on charge/discharge
- Directive-driven: no-charge hours, no-discharge hours, grid caps, reserve floors
- End-of-day: `e_after[23] = initial_energy_kwh`

Solved with CBC. Result is returned with `grid_kwh`, `solar_used_kwh`, `battery_action`, `battery_kwh`, `battery_energy_after_kwh` per hour.

### 6. Response

Final JSON includes both the interpretation and the plan. `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh` are recomputed from the plan.

---

## Troubleshooting

### `pydantic_core._pydantic_core.ValidationError: llm_provider`

Your `.env` has a typo in `LLM_PROVIDER`. Valid values:

```
openai | groq | gemini | openai_compatible
```

Fix and restart the server. **Note:** `.env` is cached by `@lru_cache`; you must restart `uvicorn` after editing.

### `openai.AuthenticationError: 401`

Your `LLM_API_KEY` is invalid. Check the provider dashboard.

### `openai.NotFoundError: 404 - model does not exist`

Your `LLM_MODEL` is wrong or deprecated. Check the provider's model list:

```bash
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

### `LLMRateLimited` / `503 Service Unavailable`

You hit the provider's rate limit. Wait for `Retry-After` seconds, or switch provider.

### `curl: option --data: error encountered when reading a file`

Your file path is wrong. `curl --data @file.json` reads from the **current directory**. Run `pwd` and `ls file.json` first.

### Server starts but `.env` values not applied

`.env` values are cached with `@lru_cache`. **Restart `uvicorn`** after editing.

### `Address already in use`

Another process on port 8000. Kill it:

```bash
lsof -i :8000
kill -9 <PID>
```

Or use a different port:

```bash
uvicorn app.main:app --port 8001
```

---

## Known Limitations

1. **Single LLM provider.** No automatic fallback to a second provider if the primary rate-limits. (Planned for later.)

2. **In-memory cache.** Cache is per-process; restarting the server clears it. For multi-worker deployments, use Redis.

3. **No persistent logging.** Logs go to stdout. For production, ship to a log aggregator.

4. **LP solver time limit.** CBC may return a sub-optimal solution on pathological inputs (time limit 10s). Public cases solve in <100ms.

5. **Time window convention.** Only whole-hour windows supported. Minutes are not part of the schema.

6. **No authentication.** The API is public and unauthenticated. Add a gateway if deploying to a sensitive environment.

7. **`.env` is cached.** Editing `.env` requires a server restart.

---

## Secret Handling

- **Never** commit `.env`, API keys, or tokens
- **Never** log raw API keys or full LLM prompts containing secrets
- `.env` is gitignored; only `.env.example` is committed
- Docker images must be built **without** baked-in secrets — pass via `--env-file` at runtime

---

## Team / Credits

- **Team:** <your team name>
- **Event:** BUP CSE Fest 2026 · Hackathon · Online Preliminary
- **Organizer:** Bangladesh University of Professionals, Mirpur Cantonment, Dhaka
- **In association with:** Poridhi
- **Libraries:** FastAPI, Pydantic, OpenAI SDK, PuLP, Tenacity, structlog

---

## License

For hackathon use only. See event rules for details.