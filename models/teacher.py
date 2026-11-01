"""Teacher representation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Teacher:
    """Teacher profile with availability, preferences, and daily workload limits."""

    teacher_id: str
    name: str
    unavailable: frozenset[tuple[int, int]] = frozenset()
    preferred: frozenset[tuple[int, int]] = frozenset()
    max_daily_sessions: int | None = None
