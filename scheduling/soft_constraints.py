"""Soft constraint evaluation and penalty reporting.

Computes soft constraint penalty metrics without altering timetable validity:
- Student gaps between sessions on the same day.
- Teacher gaps between sessions on the same day.
- Teacher workload balance (or max daily session overages).
- Teacher time preferences (slots outside preferred set).
- Assignment changes relative to a baseline timetable.

Weights default to 1.0 and are configurable via SoftWeights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from models.assignment import Assignment
from models.instance import SchedulingInstance


@dataclass(frozen=True)
class SoftWeights:
    """Configurable weights for soft constraint penalty components."""

    w_student_gap: float = 1.0
    w_teacher_gap: float = 1.0
    w_workload: float = 1.0
    w_preference: float = 1.0
    w_change: float = 1.0


@dataclass
class SoftReport:
    """Comprehensive penalty report produced by soft_penalty."""

    student_gap: float
    teacher_gap: float
    workload: float
    preference: float
    change: float
    total: float
    details: dict[str, Any] = field(default_factory=dict)


def _extract_assignment_dict(
    assignment: Mapping[str, Assignment | None] | Iterable[tuple[str, Assignment | None]] | Any,
) -> dict[str, Assignment]:
    """Normalise assignment input into a dict mapping session_id -> Assignment."""
    result: dict[str, Assignment] = {}

    if isinstance(assignment, Mapping):
        pairs = assignment.items()
    elif isinstance(assignment, Iterable):
        pairs = []
        for item in assignment:
            if isinstance(item, tuple) and len(item) == 2:
                pairs.append((str(item[0]), item[1]))
    elif hasattr(assignment, "assignments"):
        raw = getattr(assignment, "assignments")
        pairs = raw.items() if isinstance(raw, Mapping) else []
    else:
        return result

    for sid, val in pairs:
        if isinstance(val, Assignment):
            result[sid] = val
        elif isinstance(val, (tuple, list)) and len(val) >= 3:
            try:
                result[sid] = Assignment(day=int(val[0]), start_slot=int(val[1]), room_id=str(val[2]))
            except (ValueError, TypeError):
                pass

    return result


def soft_penalty(
    instance: SchedulingInstance,
    assignment: Mapping[str, Assignment | None] | Iterable[tuple[str, Assignment | None]] | Any,
    weights: SoftWeights = SoftWeights(),
    baseline: Mapping[str, Any] | None = None,
) -> SoftReport:
    """Evaluate soft constraints on a candidate timetable and compute total penalty.

    Args:
        instance: The SchedulingInstance containing curriculum, divisions, teachers, and grid.
        assignment: Schedulable assignments mapping session_id to Assignment.
        weights: Weights for linear combination of penalty terms.
        baseline: Optional baseline assignment mapping session_id -> Assignment/tuple for change penalty.

    Returns:
        SoftReport with component penalties, total weighted score, and detailed breakdowns.
    """
    if not isinstance(instance, SchedulingInstance):
        return SoftReport(
            student_gap=0.0,
            teacher_gap=0.0,
            workload=0.0,
            preference=0.0,
            change=0.0,
            total=0.0,
            details={},
        )

    asgns = _extract_assignment_dict(assignment)
    inst_sessions = {s.session_id: s for s in instance.sessions}
    num_days = instance.grid.num_days

    # 1. Student gap penalty
    # Group occupied slots by (division_id, day)
    div_day_slots: dict[tuple[str, int], set[int]] = {}
    # 2. Teacher gap penalty & workload
    # Group occupied slots and session counts by (teacher_id, day)
    teacher_day_slots: dict[tuple[str, int], set[int]] = {}
    teacher_day_counts: dict[tuple[str, int], int] = {}
    # 4. Teacher preference penalty
    pref_by_teacher: dict[str, float] = {t.teacher_id: 0.0 for t in instance.teachers.values()}

    for sid, asgn in asgns.items():
        session = inst_sessions.get(sid)
        if session is None:
            continue

        day = asgn.day
        if not (0 <= day < num_days):
            continue

        duration = session.duration_slots
        session_slots = set(range(asgn.start_slot, asgn.start_slot + duration))

        # Division slots
        div_key = (session.division_id, day)
        div_day_slots.setdefault(div_key, set()).update(session_slots)

        # Teacher slots & session count
        t_key = (session.teacher_id, day)
        teacher_day_slots.setdefault(t_key, set()).update(session_slots)
        teacher_day_counts[t_key] = teacher_day_counts.get(t_key, 0) + 1

        # Teacher preference check
        teacher = instance.teachers.get(session.teacher_id)
        if teacher is not None and teacher.preferred:
            for s in session_slots:
                if (day, s) not in teacher.preferred:
                    pref_by_teacher[teacher.teacher_id] += 1.0

    # Calculate student gap penalty: (last_slot - first_slot + 1) - num_occupied_slots
    div_gaps: dict[str, float] = {d.division_id: 0.0 for d in instance.divisions.values()}
    total_student_gap = 0.0
    for div in instance.divisions.values():
        for d in range(num_days):
            slots = div_day_slots.get((div.division_id, d), set())
            if len(slots) > 1:
                gap = float((max(slots) - min(slots) + 1) - len(slots))
                div_gaps[div.division_id] += gap
                total_student_gap += gap

    # Calculate teacher gap penalty: same formula
    teacher_gaps: dict[str, float] = {t.teacher_id: 0.0 for t in instance.teachers.values()}
    total_teacher_gap = 0.0
    for teacher in instance.teachers.values():
        for d in range(num_days):
            slots = teacher_day_slots.get((teacher.teacher_id, d), set())
            if len(slots) > 1:
                gap = float((max(slots) - min(slots) + 1) - len(slots))
                teacher_gaps[teacher.teacher_id] += gap
                total_teacher_gap += gap

    # Calculate workload imbalance penalty
    workload_by_teacher: dict[str, float] = {}
    total_workload = 0.0
    for teacher in instance.teachers.values():
        tid = teacher.teacher_id
        day_counts = [teacher_day_counts.get((tid, d), 0) for d in range(num_days)]

        if teacher.max_daily_sessions is not None:
            pen = sum(max(0, c - teacher.max_daily_sessions) for c in day_counts)
        else:
            active_loads = [c for c in day_counts if c > 0]
            if len(active_loads) <= 1:
                pen = 0
            else:
                pen = max(active_loads) - min(active_loads)

        pen_f = float(pen)
        workload_by_teacher[tid] = pen_f
        total_workload += pen_f

    # Calculate preference violation penalty
    total_preference = sum(pref_by_teacher.values())

    # Calculate change penalty relative to baseline
    changed_sids: list[str] = []
    if baseline is not None:
        for sid, session in inst_sessions.items():
            if sid in baseline:
                base_raw = baseline[sid]
                if isinstance(base_raw, Assignment):
                    base_tuple = (base_raw.day, base_raw.start_slot, base_raw.room_id)
                elif isinstance(base_raw, (tuple, list)) and len(base_raw) >= 3:
                    base_tuple = (int(base_raw[0]), int(base_raw[1]), str(base_raw[2]))
                else:
                    continue

                curr_asgn = asgns.get(sid)
                if curr_asgn is None:
                    changed_sids.append(sid)
                else:
                    curr_tuple = (curr_asgn.day, curr_asgn.start_slot, curr_asgn.room_id)
                    if curr_tuple != base_tuple:
                        changed_sids.append(sid)
            else:
                if sid in asgns:
                    changed_sids.append(sid)

    total_change = float(len(changed_sids))

    # Total weighted penalty
    total_weighted = (
        weights.w_student_gap * total_student_gap
        + weights.w_teacher_gap * total_teacher_gap
        + weights.w_workload * total_workload
        + weights.w_preference * total_preference
        + weights.w_change * total_change
    )

    details = {
        "by_division_gap": div_gaps,
        "by_teacher_gap": teacher_gaps,
        "by_teacher_workload": workload_by_teacher,
        "by_teacher_preference": pref_by_teacher,
        "changed_sessions": changed_sids,
    }

    return SoftReport(
        student_gap=total_student_gap,
        teacher_gap=total_teacher_gap,
        workload=total_workload,
        preference=total_preference,
        change=total_change,
        total=total_weighted,
        details=details,
    )
