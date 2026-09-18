"""Data structures describing the optimization problem."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DirectiveSet:
    """Directives applied before solving."""

    solar_factor_by_hour: dict[int, float] = field(default_factory=dict)
    reserve_by_hour: dict[int, float] = field(default_factory=dict)
    no_charge_hours: set[int] = field(default_factory=set)
    no_discharge_hours: set[int] = field(default_factory=set)
    max_grid_by_hour: dict[int, float] = field(default_factory=dict)

    @classmethod
    def from_validated(cls, directives: list[dict]) -> "DirectiveSet":
        ds = cls()
        for d in directives:
            if not d["applies"]:
                continue
            dtype = d["directive_type"]
            adj = d["structured_adjustment"]
            if dtype == "solar_reduction":
                for h in adj["hours"]:
                    ds.solar_factor_by_hour[h] = adj["factor"]
            elif dtype == "minimum_battery_reserve":
                for h in adj["hours"]:
                    ds.reserve_by_hour[h] = adj["minimum_energy_kwh"]
            elif dtype == "no_charge_window":
                ds.no_charge_hours.update(adj["hours"])
            elif dtype == "no_discharge_window":
                ds.no_discharge_hours.update(adj["hours"])
            elif dtype == "max_grid_window":
                for h in adj["hours"]:
                    ds.max_grid_by_hour[h] = adj["max_grid_kwh"]
        return ds

    def effective_solar(self, hour: int, base_solar: float) -> float:
        factor = self.solar_factor_by_hour.get(hour, 1.0)
        return base_solar * factor

    def effective_reserve(self, hour: int, base_min: float) -> float:
        return max(base_min, self.reserve_by_hour.get(hour, 0.0))

    def grid_cap(self, hour: int) -> Optional[float]:
        return self.max_grid_by_hour.get(hour)