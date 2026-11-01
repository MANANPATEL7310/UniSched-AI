"""Project-wide exceptions hierarchy."""
from __future__ import annotations


class TimetableError(Exception):
    """Base class for all timetable scheduling project exceptions."""
    pass


class DataLoadError(TimetableError):
    """Raised when data loading or parsing fails (malformed file, missing columns, invalid format)."""
    pass


class InputValidationError(TimetableError):
    """Raised when an instance fails input validation before search starts."""

    def __init__(self, issues: list):
        self.issues = issues
        summary = f"Input validation failed with {len(issues)} issue(s)."
        super().__init__(summary)


class GenerationError(TimetableError):
    """Raised when synthetic instance generation fails to plant a feasible solution."""
    pass


class BusyError(TimetableError):
    """Raised when another run or benchmark is already in progress."""
    pass


class NotFoundError(TimetableError):
    """Raised when an entity, sample, run, or benchmark result is not found."""
    pass
