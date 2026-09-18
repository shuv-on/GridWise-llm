"""Pytest fixtures and shared test utilities."""
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Ensure tests never hit real LLM
os.environ.setdefault("LLM_API_KEY", "test-dummy-key")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.main import app  # noqa: E402
from app.services.llm.cache import get_cache  # noqa: E402


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Reset LLM cache so tests don't leak state."""
    cache = get_cache()
    cache._store.clear()
    cache._hits = 0
    cache._misses = 0
    yield
    cache._store.clear()
    cache._hits = 0
    cache._misses = 0


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_hours() -> list[dict]:
    """24 hours of realistic test data."""
    base = [
        (100, 0, 6), (95, 0, 5), (90, 0, 4), (90, 0, 4),
        (95, 0, 4), (105, 0, 5), (120, 5, 7), (135, 20, 9),
        (145, 50, 11), (155, 90, 13), (165, 130, 15), (175, 160, 16),
        (180, 180, 16), (175, 170, 15), (165, 140, 14), (160, 90, 15),
        (170, 45, 18), (185, 10, 22), (205, 0, 28), (215, 0, 30),
        (205, 0, 26), (175, 0, 18), (135, 0, 10), (105, 0, 7),
    ]
    return [
        {"hour": h, "demand_kwh": d, "solar_kwh": s, "tariff_bdt_per_kwh": t}
        for h, (d, s, t) in enumerate(base)
    ]


@pytest.fixture
def sample_battery() -> dict:
    return {
        "capacity_kwh": 220,
        "initial_energy_kwh": 110,
        "minimum_energy_kwh": 40,
        "max_charge_kwh_per_hour": 50,
        "max_discharge_kwh_per_hour": 50,
    }


@pytest.fixture
def valid_request(sample_hours, sample_battery) -> dict:
    return {
        "scenario_id": "TEST-01",
        "operator_notes": [
            "Solar output will drop to about 20% from 1 PM to 3 PM.",
            "The cafeteria menu changes tomorrow.",
        ],
        "hours": sample_hours,
        "battery": sample_battery,
    }


@pytest.fixture
def mock_llm_response_valid() -> list[dict]:
    """Well-formed LLM output for the default valid_request notes."""
    return [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
            "explanation": "Solar reduced to 20% during 1-3 PM",
        },
        {
            "note_index": 1,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "Irrelevant",
        },
    ]


@pytest.fixture
def mock_llm(monkeypatch):
    """Patches get_llm_client to return a controllable mock."""

    class MockLLM:
        def __init__(self):
            self.response: Any = []
            self.call_count = 0

        async def interpret_notes(self, operator_notes, battery_capacity_kwh):
            self.call_count += 1
            return self.response

    mock = MockLLM()

    def fake_get_llm_client():
        return mock

    monkeypatch.setattr(
        "app.api.routes.optimize.get_llm_client",
        fake_get_llm_client,
    )
    return mock