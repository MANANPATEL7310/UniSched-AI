"""Data Transfer Object serializers converting internal models to JSON-safe dictionaries."""
from __future__ import annotations

import math
from typing import Any

from data.validator import InputIssue
from models.timetable import Entry, Timetable
from scheduling.timetable_validator import ValidationReport, ViolationType


def clean_number(val: float | int | None) -> float | int | None:
    """Sanitize float values, replacing NaN and Infinity with None for valid JSON."""
    if val is None:
        return None
    try:
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return val
    except (ValueError, TypeError):
        return None


def issue_to_dto(issue: InputIssue) -> dict[str, Any]:
    """Serialize an InputIssue to a dictionary."""
    return {
        "severity": issue.severity,
        "code": issue.code,
        "message": issue.message,
        "entity": issue.entity,
    }


def entry_to_dto(entry: Entry) -> dict[str, Any]:
    """Serialize a Timetable Entry to a dictionary."""
    return {
        "session_id": entry.session_id,
        "course_id": entry.course_id,
        "course_name": entry.course_name,
        "teacher_id": entry.teacher_id,
        "teacher_name": entry.teacher_name,
        "division_id": entry.division_id,
        "division_name": entry.division_name,
        "room_id": entry.room_id,
        "room_name": entry.room_name,
        "day": entry.day,
        "day_name": entry.day_name,
        "start_slot": entry.start_slot,
        "end_slot": entry.end_slot,
        "start_time": entry.start_time,
        "end_time": entry.end_time,
        "duration_slots": entry.duration_slots,
    }


def timetable_to_dto(timetable: Timetable | None) -> dict[str, Any] | None:
    """Serialize a Timetable to DTO dictionary with grid and entries."""
    if timetable is None:
        return None

    grid = timetable.instance.grid
    return {
        "grid": {
            "day_names": list(grid.day_names),
            "slot_starts": list(grid.slot_starts),
            "slot_ends": list(grid.slot_ends),
        },
        "entries": [entry_to_dto(e) for e in timetable.entries()],
    }


def validation_to_dto(report: ValidationReport | None) -> dict[str, Any] | None:
    """Serialize a ValidationReport ensuring all ViolationTypes appear in counts_by_type."""
    if report is None:
        return None

    counts: dict[str, int] = {}
    for vt in ViolationType:
        counts[vt.name] = report.counts_by_type.get(vt, 0)

    violations_list = [
        {
            "type": v.type.name,
            "session_ids": list(v.session_ids),
            "resource": v.resource,
            "day": v.day,
            "slot": v.slot,
            "explanation": v.explanation,
        }
        for v in report.violations
    ]

    return {
        "is_valid": report.is_valid,
        "sessions_required": report.sessions_required,
        "sessions_assigned": report.sessions_assigned,
        "counts_by_type": counts,
        "violations": violations_list,
    }


def soft_to_dto(report: Any) -> dict[str, Any] | None:
    """Serialize a soft constraint report to a dictionary."""
    if report is None:
        return None
    return {
        "student_gap": clean_number(getattr(report, "student_gap", 0.0)),
        "teacher_gap": clean_number(getattr(report, "teacher_gap", 0.0)),
        "workload": clean_number(getattr(report, "workload", 0.0)),
        "preference": clean_number(getattr(report, "preference", 0.0)),
        "change": clean_number(getattr(report, "change", 0.0)),
        "total": clean_number(getattr(report, "total", 0.0)),
    }


def metrics_to_dto(metrics: Any, runtime_s: float = 0.0, build_s: float = 0.0, peak_memory_kb: float | None = None) -> dict[str, Any]:
    """Serialize search metrics to a dictionary."""
    return {
        "nodes": getattr(metrics, "nodes", 0),
        "attempts": getattr(metrics, "attempts", 0),
        "backtracks": getattr(metrics, "backtracks", 0),
        "checks": getattr(metrics, "checks", 0),
        "values_pruned": getattr(metrics, "values_pruned", 0),
        "root_pruned": getattr(metrics, "root_pruned", 0),
        "domain_wipeouts": getattr(metrics, "domain_wipeouts", 0),
        "runtime_s": clean_number(runtime_s) or 0.0,
        "build_s": clean_number(build_s) or 0.0,
        "peak_memory_kb": clean_number(peak_memory_kb),
    }


def progress_to_dto(progress: Any, total: int = 0, elapsed_s: float = 0.0) -> dict[str, Any]:
    """Serialize progress state to a dictionary."""
    return {
        "total": total,
        "assigned": getattr(progress, "assigned", 0),
        "nodes": getattr(progress, "nodes", 0),
        "attempts": getattr(progress, "attempts", 0),
        "backtracks": getattr(progress, "backtracks", 0),
        "elapsed_s": clean_number(elapsed_s) or 0.0,
    }


def outcome_to_dto(outcome: Any, run_id: str, algorithm: str) -> dict[str, Any]:
    """Serialize ScheduleOutcome into RunOutcome dictionary."""
    status_str = getattr(outcome.status, "name", str(outcome.status))
    timetable_dto = timetable_to_dto(outcome.timetable) if status_str == "SOLVED" and outcome.timetable else None

    return {
        "run_id": run_id,
        "algorithm": algorithm,
        "status": status_str,
        "message": outcome.message,
        "is_valid": outcome.is_valid,
        "num_sessions": outcome.num_sessions,
        "metrics": metrics_to_dto(
            outcome.metrics,
            runtime_s=outcome.runtime_s,
            build_s=outcome.build_s,
            peak_memory_kb=outcome.peak_memory_kb,
        ),
        "timetable": timetable_dto,
        "validation": validation_to_dto(outcome.validation),
        "soft": soft_to_dto(outcome.soft),
    }


def diff_to_dto(d: Any) -> dict[str, Any]:
    """Serialize a SessionDiff to a dictionary."""
    return {
        "session_id": d.session_id,
        "course_name": d.course_name,
        "division_name": d.division_name,
        "teacher_name": d.teacher_name,
        "old_day": d.old_day,
        "old_slot": d.old_slot,
        "old_room_id": d.old_room_id,
        "new_day": d.new_day,
        "new_slot": d.new_slot,
        "new_room_id": d.new_room_id,
        "change_type": d.change_type,
    }

