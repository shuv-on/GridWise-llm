"""Directive type enums and structured adjustment models."""
from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class DirectiveType(str, Enum):
    SOLAR_REDUCTION = "solar_reduction"
    MINIMUM_BATTERY_RESERVE = "minimum_battery_reserve"
    NO_CHARGE_WINDOW = "no_charge_window"
    NO_DISCHARGE_WINDOW = "no_discharge_window"
    MAX_GRID_WINDOW = "max_grid_window"
    NO_OP = "no_op"


class BatteryAction(str, Enum):
    CHARGE = "charge"
    DISCHARGE = "discharge"
    IDLE = "idle"


def _validate_hours(hours: List[int]) -> List[int]:
    """Hours must be unique ints 0-23, ascending."""
    if not hours:
        raise ValueError("hours cannot be empty")
    if any(not isinstance(h, int) or h < 0 or h > 23 for h in hours):
        raise ValueError("hours must be integers in [0, 23]")
    if len(hours) != len(set(hours)):
        raise ValueError("hours must be unique")
    if hours != sorted(hours):
        raise ValueError("hours must be in ascending order")
    return hours


class SolarReductionAdj(BaseModel):
    hours: List[int]
    factor: float = Field(ge=0.0, le=1.0)

    @field_validator("hours")
    @classmethod
    def check_hours(cls, v: List[int]) -> List[int]:
        return _validate_hours(v)


class MinimumBatteryReserveAdj(BaseModel):
    hours: List[int]
    minimum_energy_kwh: float = Field(ge=0.0)

    @field_validator("hours")
    @classmethod
    def check_hours(cls, v: List[int]) -> List[int]:
        return _validate_hours(v)


class NoChargeWindowAdj(BaseModel):
    hours: List[int]

    @field_validator("hours")
    @classmethod
    def check_hours(cls, v: List[int]) -> List[int]:
        return _validate_hours(v)


class NoDischargeWindowAdj(BaseModel):
    hours: List[int]

    @field_validator("hours")
    @classmethod
    def check_hours(cls, v: List[int]) -> List[int]:
        return _validate_hours(v)


class MaxGridWindowAdj(BaseModel):
    hours: List[int]
    max_grid_kwh: float = Field(ge=0.0)

    @field_validator("hours")
    @classmethod
    def check_hours(cls, v: List[int]) -> List[int]:
        return _validate_hours(v)


# Union of all possible structured adjustment shapes
StructuredAdjustment = Union[
    SolarReductionAdj,
    MinimumBatteryReserveAdj,
    NoChargeWindowAdj,
    NoDischargeWindowAdj,
    MaxGridWindowAdj,
    None,
]


class DirectiveInterpretation(BaseModel):
    """One interpretation entry per operator note."""

    note_index: int = Field(ge=0)
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: Optional[dict] = None
    explanation: str = ""

    @field_validator("structured_adjustment")
    @classmethod
    def check_no_op_null(cls, v, info):
        # no_op must have null adjustment
        if info.data.get("directive_type") == DirectiveType.NO_OP and v is not None:
            raise ValueError("no_op requires structured_adjustment = null")
        return v