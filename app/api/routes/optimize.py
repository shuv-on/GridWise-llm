"""POST /optimize-energy endpoint: LLM -> Guardrail -> Optimizer."""
import time

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.request import OptimizeRequest
from app.schemas.response import OptimizeResponse
from app.services.guardrails.validator import validate_directives
from app.services.llm.cache import get_cache
from app.services.llm.openai_client import get_llm_client
from app.services.optimizer.energy_model import DirectiveSet
from app.services.optimizer.solver import solve

router = APIRouter(tags=["optimize"])
log = get_logger("optimize")


@router.post("/optimize-energy", response_model=OptimizeResponse)
async def optimize_energy(request: OptimizeRequest) -> OptimizeResponse:
    t0 = time.perf_counter()
    cache = get_cache()
    notes = request.operator_notes
    cap = request.battery.capacity_kwh

    # ---- 1. Check cache ----
    cached = cache.get(notes, cap)
    if cached is not None:
        validated = cached
        log.info("using_cached_interpretation")
    else:
        # ---- 2. LLM call ----
        llm = get_llm_client()
        raw_directives = await llm.interpret_notes(
            operator_notes=notes,
            battery_capacity_kwh=cap,
        )

        # ---- 3. Guardrail ----
        validated = validate_directives(
            raw_directives,
            expected_count=len(notes),
        )
        cache.put(notes, cap, validated)

    # ---- 4. Solve ----
    directive_set = DirectiveSet.from_validated(validated)
    result = solve(request, directive_set)

    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    log.info(
        "optimize_complete",
        scenario=request.scenario_id,
        elapsed_ms=elapsed,
        cache_stats=cache.stats(),
    )

    applied = [d["directive_type"] for d in validated if d["applies"]]
    summary = (
        f"Applied {len(applied)} directive(s): {', '.join(applied) or 'none'}. "
        f"Cost {result['total_cost']} BDT, peak grid {result['peak_grid']} kWh."
    )

    return OptimizeResponse(
        scenario_id=request.scenario_id,
        directive_interpretation=validated,
        hourly_plan=result["hours"],
        total_grid_kwh=result["total_grid"],
        total_cost_bdt=result["total_cost"],
        peak_grid_kwh=result["peak_grid"],
        plan_summary=summary,
    )