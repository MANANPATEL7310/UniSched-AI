"""ClassSession representation (a single schedulable atomic or multi-slot block)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.assignment import Assignment


@dataclass(frozen=True)
class ClassSession:
    """A single weekly session that needs to be scheduled."""

    session_id: str
    course_id: str
    division_id: str
    teacher_id: str
    duration_slots: int
    room_types: tuple[str, ...]
    required_capacity: int
    fixed: Assignment | None = None
