"""Student division representation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Division:
    """Student cohort/division with student count and course enrolments."""

    division_id: str
    name: str
    student_count: int
    enrolled_courses: tuple[str, ...]
