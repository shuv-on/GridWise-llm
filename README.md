# GridWise — Smart Campus Energy Optimization API

**BUP CSE Fest 2026 · Hackathon · Online Preliminary**

LLM-assisted operator directive interpretation + 24-hour energy cost optimization.

> **Live Demo:** https://gridwise-llm-qk9j.onrender.com
> **API Docs:** https://gridwise-llm-qk9j.onrender.com/docs

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
   - [Linux (Ubuntu 22.04+)](#linux-ubuntu-2204)
   - [macOS (12+)](#macos-12)
   - [Windows 11](#windows-11)
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

| Directive | Meaning |
|---|---|
| `solar_reduction` | Usable solar reduced by a factor during specific hours |
| `minimum_battery_reserve` | Battery must stay at or above a level |
| `no_charge_window` | Battery charging disabled during hours |
| `no_discharge_window` | Battery discharging disabled during hours |
| `max_grid_window` | Grid import capped during hours |
| `no_op` | Irrelevant note (ignored) |

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

## Quick Start

> **Prerequisite:** Python 3.11+ (3.12 recommended) installed on your machine.

### Linux (Ubuntu 22.04+)

#### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git
```

#### 2. Clone and enter project

```bash
git clone <your-repo-url> gridwise
cd gridwise
```

#### 3. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Configure environment

```bash
cp .env.example .env
nano .env        # paste your LLM_API_KEY
```

#### 6. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 7. Verify in another terminal

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

### macOS (12+)

#### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python 3.12

```bash
brew install python@3.12
```

#### 3. Clone and enter project

```bash
git clone <your-repo-url> gridwise
cd gridwise
```

#### 4. Create virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

#### 5. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configure environment

```bash
cp .env.example .env
open -e .env        # paste your LLM_API_KEY, save
```

#### 7. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 8. Verify in another terminal

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

> **macOS Note:** If you have Apple Silicon (M1/M2/M3), all dependencies install native. No Rosetta needed.

---

### Windows 11

#### Option A: PowerShell (recommended)

Open **PowerShell** as a normal user (not admin).

##### 1. Install Python 3.12

Download from https://www.python.org/downloads/ — **check "Add Python to PATH"** during install.

Verify:

```powershell
python --version
# Should show: Python 3.12.x
```

##### 2. Install Git (if not already installed)

Download from https://git-scm.com/download/win

##### 3. Clone and enter project

```powershell
git clone <your-repo-url> gridwise
cd gridwise
```

##### 4. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **If you see "running scripts is disabled":**
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Then activate again.

##### 5. Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

##### 6. Configure environment

```powershell
Copy-Item .env.example .env
notepad .env        # paste your LLM_API_KEY, save
```

##### 7. Start the server

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

##### 8. Verify in another PowerShell window

```powershell
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

#### Option B: Git Bash (if you prefer Unix-style commands)

##### 1. Install Git for Windows

Download from https://git-scm.com/download/win — this includes **Git Bash**.

##### 2. Open Git Bash, then

```bash
git clone <your-repo-url> gridwise
cd gridwise

python -m venv .venv
source .venv/Scripts/activate    # Note: Scripts, not bin

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
notepad .env                      # paste your LLM_API_KEY, save

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Windows Note:** In Git Bash the activate path is `.venv/Scripts/activate`, not `.venv/bin/activate`.

---

#### Option C: WSL2 (Ubuntu on Windows)

If you already have WSL2 with Ubuntu installed, follow the **Linux** steps inside WSL. This is the smoothest path if you use Docker Desktop or want identical behavior to Linux CI.

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

**Linux / macOS / Git Bash:**
```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production-style (Gunicorn)

**Linux / macOS:**
```bash
gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60
```

**Windows:** Gunicorn does not support Windows. Use **Docker** or **WSL2** for production-style runs.

### Quick helpers (Linux / macOS / Git Bash)

```bash
make install     # install dependencies
make run         # start dev server
make test        # run pytest
make smoke       # run smoke test
make samples     # run all 10 public samples
make docker      # build docker image
```

> **Windows PowerShell users:** `make` is not installed by default. Either use Git Bash (which has `make`) or run the underlying commands directly.

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
    "... 22 more entries ..."
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
      "grid_kwh": 50.0,
      "solar_used_kwh": 0.0,
      "battery_action": "discharge",
      "battery_kwh": 50.0,
      "battery_energy_after_kwh": 60.0
    },
    "... 23 more entries ..."
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
| `405` | Wrong HTTP method (e.g., GET instead of POST) |
| `422` | LLM output failed guardrails |
| `500` | Internal error |
| `503` | LLM provider rate-limited (retry with `Retry-After` header) |

---

## Testing

### Run unit tests

**Linux / macOS / Git Bash:**
```bash
source .venv/bin/activate
pytest -v
```

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
pytest -v
```

### With coverage

```bash
pytest --cov=app --cov-report=term-missing
```

### Smoke test (end-to-end)

Make sure the server is running first, then:

**Linux / macOS / Git Bash:**
```bash
bash scripts/smoke_test.sh
```

**Windows PowerShell:** Use Git Bash — `bash scripts/smoke_test.sh`.

### Run all 10 public sample cases

```bash
python3 scripts/run_public_samples.py

# Against deployed URL:
python3 scripts/run_public_samples.py --url https://gridwise-llm-qk9j.onrender.com
```

This validates:
- All 10 cases return `200 OK`
- Each response has 24 hourly entries
- Battery, energy balance, end-of-day neutrality all hold
- Directive interpretations match ground truth

**Expected result:** `10 passed, 0 failed`

---

## Docker

> **Note:** Docker Desktop must be installed.
> - **Windows 11:** https://docs.docker.com/desktop/install/windows-install/
> - **macOS:** https://docs.docker.com/desktop/install/mac-install/
> - **Linux:** https://docs.docker.com/engine/install/

### Build the image

```bash
docker build -t gridwise:latest .
```

### Run the container

**Linux / macOS:**
```bash
docker run --rm -p 8000:8000 --env-file .env gridwise:latest
```

**Windows PowerShell:**
```powershell
docker run --rm -p 8000:8000 --env-file .env gridwise:latest
```

### Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Docker Compose

```bash
docker compose up -d --build
docker compose logs -f gridwise
docker compose down
```

### Docker fallback (for organizers)

```bash
docker pull <your-registry>/gridwise:<tag>
docker run --rm -p 8000:8000 --env-file .env <your-registry>/gridwise:<tag>
```

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
├── tests/                         # pytest suite (29 tests)
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

`app/services/llm/openai_client.py` calls the provider with a strict JSON-only system prompt (`app/services/llm/prompts.py`) that:

- Enumerates all directive types and their exact `structured_adjustment` shapes
- Explains time rules (start-inclusive, end-exclusive)
- Explains percentage normalization (`80% reduction` → `factor = 0.2`)
- Requires exactly one entry per note, in `note_index` order

### 4. Guardrail validation

`app/services/guardrails/validator.py` re-validates every field:

- `directive_type` ∈ allowed set
- `hours` unique ints 0-23, ascending
- `factor` ∈ [0, 1]
- `minimum_energy_kwh`, `max_grid_kwh` ≥ 0
- `no_op` → `applies = false`, `structured_adjustment = null`
- Every other type → `applies = true`, adjustment present
- `note_index` matches position

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
- Mutual exclusion: `charge[h] + discharge[h] ≤ max_rate`
- Directive-driven: no-charge hours, no-discharge hours, grid caps, reserve floors
- End-of-day: `e_after[23] = initial_energy_kwh`

Solved with CBC. Result is returned with `grid_kwh`, `solar_used_kwh`, `battery_action`, `battery_kwh`, `battery_energy_after_kwh` per hour.

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
# Linux / macOS / Git Bash
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

```powershell
# Windows PowerShell
curl https://api.groq.com/openai/v1/models `
  -H "Authorization: Bearer $env:LLM_API_KEY"
```

### `LLMRateLimited` / `503 Service Unavailable`

You hit the provider's rate limit. Wait for `Retry-After` seconds, or switch provider.

### `curl: option --data: error encountered when reading a file`

Your file path is wrong. `curl --data @file.json` reads from the **current directory**. Run `pwd` and `ls file.json` first.

**Windows PowerShell — use `curl.exe`** (the built-in `curl` alias behaves differently):

```powershell
curl.exe -s -X POST http://localhost:8000/optimize-energy `
  -H "Content-Type: application/json" `
  --data "@body.json"
```

### `Address already in use` (Linux / macOS)

```bash
lsof -i :8000
kill -9 <PID>
```

### `Address already in use` (Windows)

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### `Set-ExecutionPolicy` error (Windows PowerShell)

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### `venv\Scripts\activate` vs `venv/bin/activate`

- **Linux / macOS / Git Bash:** `.venv/bin/activate`
- **Windows PowerShell / cmd:** `.venv\Scripts\Activate.ps1`

### Server starts but `.env` values not applied

`.env` values are cached with `@lru_cache`. **Restart `uvicorn`** after editing.

### Docker permission denied on Linux

```bash
sudo usermod -aG docker $USER
newgrp docker
# or logout / login
```

---

## Known Limitations

1. **Single LLM provider.** No automatic fallback to a second provider if the primary rate-limits. (Planned.)

2. **In-memory cache.** Per-process; restarting the server clears it. For multi-worker deployments, use Redis.

3. **No persistent logging.** Logs go to stdout. For production, ship to a log aggregator.

4. **LP solver time limit.** CBC may return a sub-optimal solution on pathological inputs (10s limit). Public cases solve in <100ms.

5. **Time window convention.** Only whole-hour windows supported.

6. **No authentication.** The API is public and unauthenticated.

7. **`.env` is cached.** Editing requires a server restart.

8. **Gunicorn not available on Windows.** Use Docker or WSL2 for production-style runs on Windows.

---

## Secret Handling

- **Never** commit `.env`, API keys, or tokens
- **Never** log raw API keys or full LLM prompts containing secrets
- `.env` is gitignored; only `.env.example` is committed
- Docker images must be built **without** baked-in secrets — pass via `--env-file` at runtime

---

## Team / Credits

- **Event:** BUP CSE Fest 2026 · Hackathon · Online Preliminary
- **Organizer:** Bangladesh University of Professionals, Mirpur Cantonment, Dhaka
- **In association with:** Poridhi
- **Libraries:** FastAPI, Pydantic, OpenAI SDK, PuLP, Tenacity, structlog

---

## License

For hackathon use only. See event rules for details.