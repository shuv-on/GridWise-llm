"""Deterministic validation of LLM output. Never trust the model."""
from typing import Any

from app.core.exceptions import GuardrailError
from app.core.logging import get_logger
from app.schemas.directives import DirectiveType
from app.utils.time_utils import is_valid_hour_list

log = get_logger("guardrail")

ALLOWED_TYPES = {d.value for d in DirectiveType}


def _require_keys(d: dict, keys: list[str], ctx: str) -> None:
    for k in keys:
        if k not in d:
            raise GuardrailError(f"{ctx}: missing key '{k}'")


def _validate_hours_field(adj: dict, ctx: str) -> list[int]:
    if "hours" not in adj:
        raise GuardrailError(f"{ctx}: missing 'hours'")
    hours = adj["hours"]
    if not isinstance(hours, list) or not is_valid_hour_list(hours):
        raise GuardrailError(f"{ctx}: invalid hours {hours}")
    return hours


def validate_one(raw: dict, expected_index: int) -> dict:
    """Validate and normalize one directive entry."""
    if not isinstance(raw, dict):
        raise GuardrailError(f"note {expected_index}: entry is not an object")

    _require_keys(raw, ["note_index", "applies", "directive_type"], f"note {expected_index}")

    if raw["note_index"] != expected_index:
        raise GuardrailError(
            f"note {expected_index}: note_index mismatch ({raw['note_index']})"
        )

    dtype = raw["directive_type"]
    if dtype not in ALLOWED_TYPES:
        raise GuardrailError(f"note {expected_index}: unknown directive '{dtype}'")

    applies = bool(raw["applies"])
    adj = raw.get("structured_adjustment")

    # ---- no_op branch ----
    if dtype == DirectiveType.NO_OP.value:
        if applies is not False:
            raise GuardrailError(f"note {expected_index}: no_op must have applies=false")
        if adj is not None:
            raise GuardrailError(f"note {expected_index}: no_op must have null adjustment")
        return {
            "note_index": expected_index,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": str(raw.get("explanation", ""))[:300],
        }

    # ---- non-no_op branch ----
    if applies is not True:
        raise GuardrailError(f"note {expected_index}: {dtype} must have applies=true")
    if not isinstance(adj, dict):
        raise GuardrailError(f"note {expected_index}: {dtype} needs structured_adjustment")

    clean_adj: dict[str, Any] = {}

    if dtype == DirectiveType.SOLAR_REDUCTION.value:
        _require_keys(adj, ["hours", "factor"], f"note {expected_index}")
        hours = _validate_hours_field(adj, f"note {expected_index}")
        factor = adj["factor"]
        if not isinstance(factor, (int, float)) or not (0.0 <= float(factor) <= 1.0):
            raise GuardrailError(f"note {expected_index}: factor must be in [0,1]")
        clean_adj = {"hours": hours, "factor": float(factor)}

    elif dtype == DirectiveType.MINIMUM_BATTERY_RESERVE.value:
        _require_keys(adj, ["hours", "minimum_energy_kwh"], f"note {expected_index}")
        hours = _validate_hours_field(adj, f"note {expected_index}")
        val = adj["minimum_energy_kwh"]
        if not isinstance(val, (int, float)) or float(val) < 0:
            raise GuardrailError(f"note {expected_index}: minimum_energy_kwh must be >= 0")
        clean_adj = {"hours": hours, "minimum_energy_kwh": float(val)}

    elif dtype in (
        DirectiveType.NO_CHARGE_WINDOW.value,
        DirectiveType.NO_DISCHARGE_WINDOW.value,
    ):
        hours = _validate_hours_field(adj, f"note {expected_index}")
        clean_adj = {"hours": hours}

    elif dtype == DirectiveType.MAX_GRID_WINDOW.value:
        _require_keys(adj, ["hours", "max_grid_kwh"], f"note {expected_index}")
        hours = _validate_hours_field(adj, f"note {expected_index}")
        val = adj["max_grid_kwh"]
        if not isinstance(val, (int, float)) or float(val) < 0:
            raise GuardrailError(f"note {expected_index}: max_grid_kwh must be >= 0")
        clean_adj = {"hours": hours, "max_grid_kwh": float(val)}

    else:
        raise GuardrailError(f"note {expected_index}: unhandled type {dtype}")

    return {
        "note_index": expected_index,
        "applies": True,
        "directive_type": dtype,
        "structured_adjustment": clean_adj,
        "explanation": str(raw.get("explanation", ""))[:300],
    }


def validate_directives(raw_directives: list[dict], expected_count: int) -> list[dict]:
    """Validate the full list in order. Raise on any violation."""
    if not isinstance(raw_directives, list):
        raise GuardrailError("directives must be a list")
    if len(raw_directives) != expected_count:
        raise GuardrailError(
            f"expected {expected_count} directives, got {len(raw_directives)}"
        )

    cleaned = []
    for i, raw in enumerate(raw_directives):
        cleaned.append(validate_one(raw, i))

    log.info("guardrail_passed", count=len(cleaned))
    return cleaned