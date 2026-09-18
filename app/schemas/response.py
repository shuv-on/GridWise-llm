"""Response schema for POST /optimize-energy."""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.directives import BatteryAction, DirectiveInterpretation


class HourlyPlanEntry(BaseModel):
    hour: int = Field(ge=0, le=23)
    grid_kwh: float = Field(ge=0.0)
    solar_used_kwh: float = Field(ge=0.0)
    battery_action: BatteryAction
    battery_kwh: float = Field(ge=0.0)
    battery_energy_after_kwh: float = Field(ge=0.0)


class OptimizeResponse(BaseModel):
    scenario_id: str
    directive_interpretation: List[DirectiveInterpretation]
    hourly_plan: List[HourlyPlanEntry]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None