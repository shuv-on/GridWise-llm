"""Request schema for POST /optimize-energy."""
from typing import List

from pydantic import BaseModel, Field, field_validator


class HourEntry(BaseModel):
    hour: int = Field(ge=0, le=23)
    demand_kwh: float = Field(ge=0.0)
    solar_kwh: float = Field(ge=0.0)
    tariff_bdt_per_kwh: float = Field(ge=0.0)


class Battery(BaseModel):
    capacity_kwh: float = Field(gt=0.0)
    initial_energy_kwh: float = Field(ge=0.0)
    minimum_energy_kwh: float = Field(ge=0.0)
    max_charge_kwh_per_hour: float = Field(gt=0.0)
    max_discharge_kwh_per_hour: float = Field(gt=0.0)

    @field_validator("initial_energy_kwh")
    @classmethod
    def check_initial(cls, v, info):
        cap = info.data.get("capacity_kwh")
        if cap is not None and v > cap:
            raise ValueError("initial_energy_kwh cannot exceed capacity_kwh")
        return v


class OptimizeRequest(BaseModel):
    scenario_id: str = Field(min_length=1)
    operator_notes: List[str] = Field(min_length=1, max_length=3)
    hours: List[HourEntry] = Field(min_length=24, max_length=24)
    battery: Battery

    @field_validator("operator_notes")
    @classmethod
    def check_notes_non_empty(cls, v: List[str]) -> List[str]:
        for note in v:
            if not note or not note.strip():
                raise ValueError("operator_notes cannot contain empty strings")
        return v

    @field_validator("hours")
    @classmethod
    def check_hours_complete(cls, v: List[HourEntry]) -> List[HourEntry]:
        seen = sorted(h.hour for h in v)
        if seen != list(range(24)):
            raise ValueError("hours must contain exactly 0..23, each once")
        return v