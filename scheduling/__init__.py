"""Scheduling and timetable validation package."""
from __future__ import annotations

from scheduling.scheduler import (
    RunHandle,
    ScheduleOutcome,
    generate_timetable,
    start_run,
)
from scheduling.timetable_validator import (
    ValidationReport,
    Violation,
    ViolationType,
    validate_timetable,
)

__all__ = [
    "ValidationReport",
    "Violation",
    "ViolationType",
    "validate_timetable",
    "ScheduleOutcome",
    "RunHandle",
    "generate_timetable",
    "start_run",
]

