#!/usr/bin/env python3
"""Run all public sample cases against a running server.

Usage:
    python3 scripts/run_public_samples.py [--url http://localhost:8000] [--file data/public_samples.json]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def load_cases(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases", [])


def validate_response(body: dict, scenario_input: dict) -> list[str]:
    """Return list of errors (empty if valid)."""
    errors: list[str] = []

    # Top-level fields
    for key in (
        "scenario_id",
        "directive_interpretation",
        "hourly_plan",
        "total_grid_kwh",
        "total_cost_bdt",
        "peak_grid_kwh",
        "plan_summary",
    ):
        if key not in body:
            errors.append(f"missing top-level key: {key}")

    if errors:
        return errors

    # scenario_id echo
    if body["scenario_id"] != scenario_input["scenario_id"]:
        errors.append("scenario_id mismatch")

    # Interpretation count
    notes = scenario_input["operator_notes"]
    if len(body["directive_interpretation"]) != len(notes):
        errors.append(
            f"directive count {len(body['directive_interpretation'])} "
            f"!= notes {len(notes)}"
        )

    # Interpretation order
    for i, d in enumerate(body["directive_interpretation"]):
        if d.get("note_index") != i:
            errors.append(f"note_index out of order at position {i}")

    # Hourly plan
    plan = body["hourly_plan"]
    if len(plan) != 24:
        errors.append(f"hourly_plan has {len(plan)} entries, expected 24")
    else:
        hours = [p["hour"] for p in plan]
        if hours != list(range(24)):
            errors.append("hours not 0..23 in order")

        # Energy balance
        hours_input = scenario_input["hours"]
        for i, p in enumerate(plan):
            hi = hours_input[i]
            supply = p["grid_kwh"] + p["solar_used_kwh"]
            if p["battery_action"] == "discharge":
                supply += p["battery_kwh"]
            demand = hi["demand_kwh"]
            if p["battery_action"] == "charge":
                demand += p["battery_kwh"]
            if abs(supply - demand) > 0.05:
                errors.append(f"hour {i}: balance off by {supply - demand:.3f}")

        # End-of-day neutrality
        if abs(plan[-1]["battery_energy_after_kwh"] - scenario_input["battery"]["initial_energy_kwh"]) > 0.05:
            errors.append("end-of-day battery not neutral")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument(
        "--file",
        default="data/public_samples.json",
        type=Path,
    )
    args = parser.parse_args()

    cases = load_cases(args.file)
    if not cases:
        print(f"No cases loaded from {args.file}")
        return 1

    print(f"Running {len(cases)} cases against {args.url}")
    print("=" * 60)

    passed = 0
    failed = 0
    total_ms = 0.0

    with httpx.Client(timeout=60.0) as client:
        # Health check
        try:
            r = client.get(f"{args.url}/health")
            if r.status_code != 200 or r.json().get("status") != "ok":
                print(f"FAIL: /health not ready: {r.status_code} {r.text}")
                return 1
        except Exception as exc:
            print(f"FAIL: cannot reach server: {exc}")
            return 1

        for case in cases:
            case_id = case.get("id", "UNKNOWN")
            scenario = case["input"]

            t0 = time.perf_counter()
            try:
                r = client.post(f"{args.url}/optimize-energy", json=scenario)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                total_ms += elapsed_ms
            except Exception as exc:
                print(f"[FAIL] {case_id}: request error: {exc}")
                failed += 1
                continue

            if r.status_code != 200:
                print(f"[FAIL] {case_id}: HTTP {r.status_code}")
                print(f"       body: {r.text[:200]}")
                failed += 1
                continue

            body = r.json()
            errors = validate_response(body, scenario)

            if errors:
                print(f"[FAIL] {case_id}: {len(errors)} validation errors")
                for e in errors[:3]:
                    print(f"       - {e}")
                failed += 1
            else:
                print(
                    f"[PASS] {case_id}: cost={body['total_cost_bdt']:.1f} BDT "
                    f"peak={body['peak_grid_kwh']:.1f} kWh ({elapsed_ms:.0f}ms)"
                )
                passed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    if cases:
        print(f"Average latency: {total_ms / len(cases):.0f}ms")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())