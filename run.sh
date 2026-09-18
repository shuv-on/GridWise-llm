#!/usr/bin/env bash
# One-command start for local development.
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PORT="${PORT:-8000}"

# ---------- Sanity ----------
if [ ! -d "$VENV" ]; then
  echo "==> Creating virtual environment"
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Installing dependencies (quiet)"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ---------- Env ----------
if [ ! -f ".env" ]; then
  echo "==> No .env found — copying from .env.example"
  cp .env.example .env
  echo ""
  echo "!!  Edit .env and set LLM_API_KEY before running."
  echo "!!  Then run this script again."
  exit 1
fi

if ! grep -q "^LLM_API_KEY=." .env; then
  echo "!!  LLM_API_KEY not set in .env"
  exit 1
fi

# ---------- Run ----------
echo ""
echo "==> Starting GridWise on http://localhost:${PORT}"
echo "==> Docs: http://localhost:${PORT}/docs"
echo "==> Health: http://localhost:${PORT}/health"
echo ""
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload