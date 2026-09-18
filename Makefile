.PHONY: help install run run-prod test test-cov smoke samples docker docker-run docker-stop docker-logs clean lint format check

# ---------- Config ----------
PYTHON ?= python3
VENV   ?= .venv
ACTIVATE = source $(VENV)/bin/activate
PORT   ?= 8000
IMAGE  ?= gridwise:latest

help:
	@echo "GridWise — available commands:"
	@echo ""
	@echo "  make install      Create venv and install dependencies"
	@echo "  make run          Run dev server with reload"
	@echo "  make run-prod     Run prod server (no reload)"
	@echo "  make test         Run pytest"
	@echo "  make test-cov     Run pytest with coverage"
	@echo "  make smoke        Run end-to-end smoke test (server must be up)"
	@echo "  make samples      Run all 10 public sample cases"
	@echo "  make docker       Build Docker image"
	@echo "  make docker-run   Run Docker container"
	@echo "  make docker-stop  Stop Docker container"
	@echo "  make docker-logs  Tail Docker logs"
	@echo "  make clean        Remove __pycache__, .pytest_cache"
	@echo "  make lint         Run ruff (if installed)"
	@echo "  make format       Run ruff format (if installed)"
	@echo "  make check        Run tests + smoke + samples"

# ---------- Dev ----------
install:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip
	$(ACTIVATE) && pip install -r requirements.txt

run:
	$(ACTIVATE) && uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload

run-prod:
	$(ACTIVATE) && uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --workers 2

# ---------- Test ----------
test:
	$(ACTIVATE) && pytest -v

test-cov:
	$(ACTIVATE) && pytest --cov=app --cov-report=term-missing

smoke:
	bash scripts/smoke_test.sh

samples:
	$(ACTIVATE) && python3 scripts/run_public_samples.py

check: test smoke samples

# ---------- Docker ----------
docker:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p $(PORT):8000 --env-file .env $(IMAGE)

docker-stop:
	-docker stop gridwise-api
	-docker rm gridwise-api

docker-logs:
	docker logs -f gridwise-api

# ---------- Utility ----------
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov .coverage

lint:
	$(ACTIVATE) && ruff check app/ tests/ scripts/

format:
	$(ACTIVATE) && ruff format app/ tests/ scripts/