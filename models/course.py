"""Course representation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    """Course definition including weekly frequency, duration in slots, and division eligibility."""

    course_id: str
    name: str
    teacher_id: str
    sessions_per_week: int
    duration_slots: int
    room_types: tuple[str, ...]
    eligible_divisions: tuple[str, ...]
