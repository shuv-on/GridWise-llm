"""Abstract LLM interface."""
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Any LLM provider must implement this."""

    @abstractmethod
    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery_capacity_kwh: float,
    ) -> list[dict]:
        """Return list of raw directive dicts (one per note)."""
        raise NotImplementedError