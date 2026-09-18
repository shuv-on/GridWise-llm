"""Integration tests for POST /optimize-energy (LLM mocked)."""


def test_valid_request_returns_200(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid
    resp = client.post("/optimize-energy", json=valid_request)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["scenario_id"] == valid_request["scenario_id"]
    assert len(body["directive_interpretation"]) == len(valid_request["operator_notes"])
    assert len(body["hourly_plan"]) == 24
    assert body["total_grid_kwh"] >= 0
    assert body["total_cost_bdt"] >= 0
    assert body["peak_grid_kwh"] >= 0


def test_hourly_plan_has_unique_hours(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid
    resp = client.post("/optimize-energy", json=valid_request)
    plan = resp.json()["hourly_plan"]
    hours = [p["hour"] for p in plan]
    assert hours == list(range(24))


def test_energy_balance_per_hour(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid
    resp = client.post("/optimize-energy", json=valid_request)
    plan = resp.json()["hourly_plan"]

    for i, p in enumerate(plan):
        hour_input = valid_request["hours"][i]
        supply = p["grid_kwh"] + p["solar_used_kwh"]
        if p["battery_action"] == "discharge":
            supply += p["battery_kwh"]
        demand = hour_input["demand_kwh"]
        if p["battery_action"] == "charge":
            demand += p["battery_kwh"]
        assert abs(supply - demand) < 0.02, f"hour {i}: {supply} != {demand}"


def test_end_of_day_neutrality(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid
    resp = client.post("/optimize-energy", json=valid_request)
    plan = resp.json()["hourly_plan"]
    final_energy = plan[-1]["battery_energy_after_kwh"]
    initial_energy = valid_request["battery"]["initial_energy_kwh"]
    assert abs(final_energy - initial_energy) < 0.02


def test_battery_bounds_respected(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid
    resp = client.post("/optimize-energy", json=valid_request)
    plan = resp.json()["hourly_plan"]
    battery = valid_request["battery"]

    for p in plan:
        assert p["battery_energy_after_kwh"] >= battery["minimum_energy_kwh"] - 0.02
        assert p["battery_energy_after_kwh"] <= battery["capacity_kwh"] + 0.02


def test_totals_recalculated_from_plan(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid
    resp = client.post("/optimize-energy", json=valid_request)
    body = resp.json()
    plan = body["hourly_plan"]
    hours_input = valid_request["hours"]

    expected_grid = sum(p["grid_kwh"] for p in plan)
    expected_cost = sum(p["grid_kwh"] * hours_input[p["hour"]]["tariff_bdt_per_kwh"] for p in plan)
    expected_peak = max(p["grid_kwh"] for p in plan)

    assert abs(body["total_grid_kwh"] - expected_grid) < 0.02
    assert abs(body["total_cost_bdt"] - expected_cost) < 0.05
    assert abs(body["peak_grid_kwh"] - expected_peak) < 0.02


def test_invalid_request_rejected(client):
    resp = client.post("/optimize-energy", json={"scenario_id": "x"})
    assert resp.status_code == 422


def test_empty_operator_notes_rejected(client, sample_hours, sample_battery):
    bad = {
        "scenario_id": "X",
        "operator_notes": [],
        "hours": sample_hours,
        "battery": sample_battery,
    }
    resp = client.post("/optimize-energy", json=bad)
    assert resp.status_code == 422


def test_too_many_notes_rejected(client, sample_hours, sample_battery):
    bad = {
        "scenario_id": "X",
        "operator_notes": ["a", "b", "c", "d"],
        "hours": sample_hours,
        "battery": sample_battery,
    }
    resp = client.post("/optimize-energy", json=bad)
    assert resp.status_code == 422


def test_wrong_hour_count_rejected(client, sample_battery):
    bad = {
        "scenario_id": "X",
        "operator_notes": ["test"],
        "hours": [{"hour": 0, "demand_kwh": 1, "solar_kwh": 0, "tariff_bdt_per_kwh": 1}],
        "battery": sample_battery,
    }
    resp = client.post("/optimize-energy", json=bad)
    assert resp.status_code == 422


def test_guardrail_failure_returns_422(client, valid_request, mock_llm):
    # LLM returns nonsense
    mock_llm.response = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "magic_type",
            "structured_adjustment": {"hours": [1]},
        },
        {
            "note_index": 1,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
        },
    ]
    resp = client.post("/optimize-energy", json=valid_request)
    assert resp.status_code == 422


def test_cache_used_on_repeat(client, valid_request, mock_llm, mock_llm_response_valid):
    mock_llm.response = mock_llm_response_valid

    client.post("/optimize-energy", json=valid_request)
    client.post("/optimize-energy", json=valid_request)

    # LLM should have been called only once (2nd hit cache)
    assert mock_llm.call_count == 1