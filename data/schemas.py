"""CSV schemas, column definitions, and formatting utilities."""
from __future__ import annotations

from typing import Iterable, Sequence

from errors import DataLoadError

# Allowed room types across the system
ROOM_TYPES: tuple[str, ...] = ("lecture", "computer_lab", "general_lab")

# CSV file requirements
REQUIRED_CSV_FILES: tuple[str, ...] = (
    "days.csv",
    "slots.csv",
    "teachers.csv",
    "courses.csv",
    "divisions.csv",
    "rooms.csv",
)
OPTIONAL_CSV_FILES: tuple[str, ...] = ("fixed_assignments.csv",)
ALL_CSV_FILES: tuple[str, ...] = REQUIRED_CSV_FILES + OPTIONAL_CSV_FILES

# Exact column definitions per CSV file
DAYS_COLUMNS: tuple[str, ...] = ("day_name",)
SLOTS_COLUMNS: tuple[str, ...] = ("start_time", "end_time")
TEACHERS_COLUMNS: tuple[str, ...] = (
    "teacher_id",
    "teacher_name",
    "unavailable_slots",
    "preferred_slots",
    "max_daily_sessions",
)
COURSES_COLUMNS: tuple[str, ...] = (
    "course_id",
    "course_name",
    "teacher_id",
    "sessions_per_week",
    "duration_slots",
    "room_types",
    "eligible_divisions",
)
DIVISIONS_COLUMNS: tuple[str, ...] = (
    "division_id",
    "division_name",
    "student_count",
    "enrolled_courses",
)
ROOMS_COLUMNS: tuple[str, ...] = (
    "room_id",
    "room_name",
    "room_type",
    "capacity",
    "unavailable_slots",
)
FIXED_ASSIGNMENTS_COLUMNS: tuple[str, ...] = (
    "session_id",
    "day_name",
    "start_time",
    "room_id",
)

CSV_FILE_COLUMNS: dict[str, tuple[str, ...]] = {
    "days.csv": DAYS_COLUMNS,
    "slots.csv": SLOTS_COLUMNS,
    "teachers.csv": TEACHERS_COLUMNS,
    "courses.csv": COURSES_COLUMNS,
    "divisions.csv": DIVISIONS_COLUMNS,
    "rooms.csv": ROOMS_COLUMNS,
    "fixed_assignments.csv": FIXED_ASSIGNMENTS_COLUMNS,
}


def split_list_cell(text: str | None) -> list[str]:
    """Split a semicolon-delimited list cell, stripping whitespace and discarding empties."""
    if not text:
        return []
    items = [item.strip() for item in text.split(";")]
    return [item for item in items if item]


def join_list_cell(items: Iterable[str]) -> str:
    """Join items into a semicolon-delimited cell string."""
    return ";".join(items)


def format_slot(day_name: str, start_time: str) -> str:
    """Format day and start time into slot identifier, e.g. 'Mon@09:00'."""
    return f"{day_name}@{start_time}"


def parse_slot_string(text: str) -> tuple[str, str]:
    """Parse a slot string like 'Mon@09:00' into (day_name, start_time).
    
    Raises:
        DataLoadError: if format is invalid.
    """
    if not text or "@" not in text:
        raise DataLoadError(f"Invalid slot string format '{text}', expected 'DayName@HH:MM'")
    day_name, start_time = text.split("@", 1)
    day_name = day_name.strip()
    start_time = start_time.strip()
    if not day_name or not start_time:
        raise DataLoadError(f"Invalid slot string format '{text}', expected 'DayName@HH:MM'")
    return day_name, start_time
