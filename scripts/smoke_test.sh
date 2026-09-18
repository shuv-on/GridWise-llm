#!/usr/bin/env bash
# End-to-end smoke test. Requires a running server on $BASE_URL.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SCENARIO_FILE="${1:-body.json}"

echo "==============================================="
echo " GridWise Smoke Test"
echo " Base URL: $BASE_URL"
echo " Scenario: $SCENARIO_FILE"
echo "==============================================="

# 1. Health
echo ""
echo "[1/4] GET /health"
HEALTH_CODE=$(curl -s -o /tmp/gw_health.json -w "%{http_code}" "$BASE_URL/health")
if [ "$HEALTH_CODE" != "200" ]; then
  echo "  FAIL: expected 200, got $HEALTH_CODE"
  cat /tmp/gw_health.json
  exit 1
fi
echo "  OK: $(cat /tmp/gw_health.json)"

# 2. Optimize energy
echo ""
echo "[2/4] POST /optimize-energy"
if [ ! -f "$SCENARIO_FILE" ]; then
  echo "  FAIL: scenario file not found: $SCENARIO_FILE"
  exit 1
fi

T0=$(date +%s%N)
RESP_CODE=$(curl -s -o /tmp/gw_response.json -w "%{http_code}" \
  -X POST "$BASE_URL/optimize-energy" \
  -H "Content-Type: application/json" \
  --data @"$SCENARIO_FILE")
T1=$(date +%s%N)
ELAPSED_MS=$(( (T1 - T0) / 1000000 ))

if [ "$RESP_CODE" != "200" ]; then
  echo "  FAIL: expected 200, got $RESP_CODE"
  cat /tmp/gw_response.json
  exit 1
fi
echo "  OK: 200 in ${ELAPSED_MS}ms"

# 3. Validate response
echo ""
echo "[3/4] Validate response structure"
python3 - <<'PY'
import json, sys

with open("/tmp/gw_response.json", encoding="utf-8") as f:
    body = json.load(f)

required = [
    "scenario_id",
    "directive_interpretation",
    "hourly_plan",
    "total_grid_kwh",
    "total_cost_bdt",
    "peak_grid_kwh",
    "plan_summary",
]
for key in required:
    assert key in body, f"missing top-level key: {key}"

assert len(body["hourly_plan"]) == 24, "hourly_plan must have 24 entries"
hours = [p["hour"] for p in body["hourly_plan"]]
assert hours == list(range(24)), "hours must be 0..23 in order"

for p in body["hourly_plan"]:
    assert p["grid_kwh"] >= 0
    assert p["solar_used_kwh"] >= 0
    assert p["battery_kwh"] >= 0
    assert p["battery_energy_after_kwh"] >= 0
    assert p["battery_action"] in ("charge", "discharge", "idle")

print("  OK: response structure valid")
print(f"  - notes interpreted: {len(body['directive_interpretation'])}")
print(f"  - total grid: {body['total_grid_kwh']} kWh")
print(f"  - total cost: {body['total_cost_bdt']} BDT")
print(f"  - peak grid:  {body['peak_grid_kwh']} kWh")
PY

# 4. Re-run for cache
echo ""
echo "[4/4] Repeat POST (cache hit expected)"
T0=$(date +%s%N)
curl -s -o /dev/null -X POST "$BASE_URL/optimize-energy" \
  -H "Content-Type: application/json" \
  --data @"$SCENARIO_FILE"
T1=$(date +%s%N)
ELAPSED_MS=$(( (T1 - T0) / 1000000 ))
echo "  OK: 200 in ${ELAPSED_MS}ms (should be much faster than step 2)"

echo ""
echo "==============================================="
echo " SMOKE TEST PASSED"
echo "==============================================="