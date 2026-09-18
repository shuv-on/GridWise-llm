"""Helpers for hour-window parsing and normalization."""
from typing import List


def normalize_hours(hours: List[int]) -> List[int]:
    """Sort and dedupe hours."""
    return sorted(set(int(h) for h in hours))


def window_to_hours(start_hour: int, end_hour: int) -> List[int]:
    """
    Convert start-inclusive, end-exclusive window into hour list.
    Example: (13, 15) -> [13, 14]
    """
    if start_hour < 0 or end_hour > 24 or start_hour >= end_hour:
        raise ValueError(f"invalid window: {start_hour} -> {end_hour}")
    return list(range(start_hour, end_hour))


def is_valid_hour_list(hours: List[int]) -> bool:
    """Hours must be unique ints 0-23 in ascending order."""
    if not hours:
        return False
    if any(not isinstance(h, int) or h < 0 or h > 23 for h in hours):
        return False
    if len(hours) != len(set(hours)):
        return False
    return hours == sorted(hours)