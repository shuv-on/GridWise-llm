"""Simple in-memory cache for LLM interpretations.

Key = hash(operator_notes + battery_capacity)
Value = validated directive list

This avoids re-calling the LLM when the same notes arrive again.
"""
import hashlib
import json
from collections import OrderedDict
from threading import Lock
from typing import Optional

from app.core.logging import get_logger

log = get_logger("llm_cache")


class InterpretationCache:
    """Thread-safe LRU cache with a fixed max size."""

    def __init__(self, max_size: int = 256) -> None:
        self._max = max_size
        self._store: OrderedDict[str, list[dict]] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(operator_notes: list[str], battery_capacity_kwh: float) -> str:
        payload = json.dumps(
            {
                "notes": [n.strip().lower() for n in operator_notes],
                "cap": round(float(battery_capacity_kwh), 4),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(
        self,
        operator_notes: list[str],
        battery_capacity_kwh: float,
    ) -> Optional[list[dict]]:
        key = self._make_key(operator_notes, battery_capacity_kwh)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._hits += 1
                log.info("llm_cache_hit", hits=self._hits, misses=self._misses)
                return self._store[key]
            self._misses += 1
            return None

    def put(
        self,
        operator_notes: list[str],
        battery_capacity_kwh: float,
        directives: list[dict],
    ) -> None:
        key = self._make_key(operator_notes, battery_capacity_kwh)
        with self._lock:
            self._store[key] = directives
            self._store.move_to_end(key)
            if len(self._store) > self._max:
                self._store.popitem(last=False)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total else 0.0,
            }


# Module-level singleton
_cache = InterpretationCache(max_size=512)


def get_cache() -> InterpretationCache:
    return _cache