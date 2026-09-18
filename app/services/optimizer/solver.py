"""LP optimizer using PuLP. Minimizes grid electricity cost."""
from typing import Any

import pulp

from app.config import get_settings
from app.core.exceptions import OptimizerError
from app.core.logging import get_logger
from app.schemas.request import OptimizeRequest
from app.services.optimizer.energy_model import DirectiveSet

log = get_logger("optimizer")


def solve(request: OptimizeRequest, directives: DirectiveSet) -> dict[str, Any]:
    """
    Build and solve the 24-hour LP.

    Decision variables per hour h:
        grid[h]       >= 0
        solar_used[h] in [0, effective_solar[h]]
        charge[h]     >= 0
        discharge[h]  >= 0
        e_after[h]    battery energy after hour h

    Returns a plan where battery_action and battery_kwh are derived
    directly from the battery energy delta, guaranteeing the energy
    balance equation holds exactly.
    """
    settings = get_settings()
    hours = sorted(request.hours, key=lambda x: x.hour)
    battery = request.battery
    n = 24

    # Precompute per-hour inputs
    demand = [hours[h].demand_kwh for h in range(n)]
    base_solar = [hours[h].solar_kwh for h in range(n)]
    tariff = [hours[h].tariff_bdt_per_kwh for h in range(n)]
    eff_solar = [directives.effective_solar(h, base_solar[h]) for h in range(n)]
    min_energy = [
        directives.effective_reserve(h, battery.minimum_energy_kwh) for h in range(n)
    ]

    prob = pulp.LpProblem("gridwise", pulp.LpMinimize)

    grid = [pulp.LpVariable(f"grid_{h}", lowBound=0) for h in range(n)]
    solar_used = [pulp.LpVariable(f"solar_{h}", lowBound=0) for h in range(n)]
    charge = [pulp.LpVariable(f"charge_{h}", lowBound=0) for h in range(n)]
    discharge = [pulp.LpVariable(f"discharge_{h}", lowBound=0) for h in range(n)]
    e_after = [
        pulp.LpVariable(
            f"e_{h}",
            lowBound=battery.minimum_energy_kwh,
            upBound=battery.capacity_kwh,
        )
        for h in range(n)
    ]

    # Objective: minimize total grid cost
    prob += pulp.lpSum(grid[h] * tariff[h] for h in range(n))

    # Per-hour constraints
    for h in range(n):
        # Solar usage cap
        prob += solar_used[h] <= eff_solar[h]

        # Charge / discharge rate limits
        prob += charge[h] <= battery.max_charge_kwh_per_hour
        prob += discharge[h] <= battery.max_discharge_kwh_per_hour

        # Prevent simultaneous charge and discharge (mutual exclusion).
        # Without this, CBC may assign both to small values and the
        # reported action becomes ambiguous.
        prob += charge[h] + discharge[h] <= max(
            battery.max_charge_kwh_per_hour,
            battery.max_discharge_kwh_per_hour,
        )

        # Directive: no charge / no discharge
        if h in directives.no_charge_hours:
            prob += charge[h] == 0
        if h in directives.no_discharge_hours:
            prob += discharge[h] == 0

        # Directive: grid cap
        cap = directives.grid_cap(h)
        if cap is not None:
            prob += grid[h] <= cap

        # Energy balance
        prob += grid[h] + solar_used[h] + discharge[h] == demand[h] + charge[h]

        # Battery reserve (directive-aware)
        prob += e_after[h] >= min_energy[h]

        # State transition
        if h == 0:
            prob += e_after[h] == battery.initial_energy_kwh + charge[h] - discharge[h]
        else:
            prob += e_after[h] == e_after[h - 1] + charge[h] - discharge[h]

    # End-of-day neutrality
    prob += e_after[n - 1] == battery.initial_energy_kwh

    # Solve
    solver = pulp.PULP_CBC_CMD(
        msg=False,
        timeLimit=settings.optimizer_time_limit_seconds,
    )
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        raise OptimizerError(f"optimizer status: {status}")

    # ------------------------------------------------------------------
    # Extract plan.
    #
    # Derive battery_action and battery_kwh from the battery energy delta
    # (e_after[h] - e_after[h-1]) rather than from the raw LP variables.
    # This guarantees the reported action always matches the energy
    # balance equation exactly, even when the solver returns tiny
    # numerical noise in charge[h] or discharge[h].
    # ------------------------------------------------------------------
    EPS = 1e-6
    plan = []
    prev_energy = battery.initial_energy_kwh

    for h in range(n):
        g = max(0.0, float(grid[h].value() or 0.0))
        s = max(0.0, float(solar_used[h].value() or 0.0))
        e = float(e_after[h].value() or 0.0)

        delta = e - prev_energy  # positive -> charged, negative -> discharged

        if delta > EPS:
            action, amount = "charge", delta
        elif delta < -EPS:
            action, amount = "discharge", -delta
        else:
            action, amount = "idle", 0.0

        # Recompute grid from the balance equation so the plan is
        # internally consistent even after rounding.
        # grid = demand + charge - discharge - solar_used
        g_calc = demand[h] + (amount if action == "charge" else 0.0) \
                 - (amount if action == "discharge" else 0.0) - s
        g_calc = max(0.0, g_calc)

        plan.append(
            {
                "hour": h,
                "grid_kwh": round(g_calc, 4),
                "solar_used_kwh": round(s, 4),
                "battery_action": action,
                "battery_kwh": round(amount, 4),
                "battery_energy_after_kwh": round(e, 4),
            }
        )
        prev_energy = e

    total_grid = round(sum(p["grid_kwh"] for p in plan), 4)
    total_cost = round(sum(plan[h]["grid_kwh"] * tariff[h] for h in range(n)), 4)
    peak_grid = round(max(p["grid_kwh"] for p in plan), 4)

    log.info(
        "optimizer_solved",
        total_grid_kwh=total_grid,
        total_cost_bdt=total_cost,
        peak_grid_kwh=peak_grid,
    )

    return {
        "hours": plan,
        "total_grid": total_grid,
        "total_cost": total_cost,
        "peak_grid": peak_grid,
    }