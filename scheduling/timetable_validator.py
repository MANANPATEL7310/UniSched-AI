"""Independent timetable validator using interval arithmetic."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from models.assignment import Assignment
from models.instance import SchedulingInstance


class ViolationType(Enum):
    """Enumeration of all possible hard constraint violations in a timetable."""

    MISSING_SESSION = "MISSING_SESSION"
    DUPLICATE_SESSION = "DUPLICATE_SESSION"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"
    TEACHER_CONFLICT = "TEACHER_CONFLICT"
    DIVISION_CONFLICT = "DIVISION_CONFLICT"
    ROOM_CONFLICT = "ROOM_CONFLICT"
    CAPACITY = "CAPACITY"
    ROOM_TYPE = "ROOM_TYPE"
    TEACHER_UNAVAILABLE = "TEACHER_UNAVAILABLE"
    ROOM_UNAVAILABLE = "ROOM_UNAVAILABLE"
    DURATION = "DURATION"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    UNKNOWN_ROOM = "UNKNOWN_ROOM"
    FIXED_ASSIGNMENT = "FIXED_ASSIGNMENT"


@dataclass(frozen=True)
class Violation:
    """A specific rule violation detected in a candidate timetable."""

    type: ViolationType
    session_ids: tuple[str, ...]
    resource: str | None
    day: int | None
    slot: int | None
    explanation: str


@dataclass
class ValidationReport:
    """Overall outcome of timetable validation."""

    is_valid: bool
    violations: list[Violation]
    counts_by_type: dict[ViolationType, int]
    sessions_required: int
    sessions_assigned: int


def validate_timetable(
    instance: SchedulingInstance,
    assignment: Mapping[str, Assignment | None] | Iterable[tuple[str, Assignment | None]] | Any,
) -> ValidationReport:
    """Independently validate a timetable against all hard constraints.
    
    Uses pure interval arithmetic and never imports from csp/. Never raises on bad or malformed input.
    """
    violations: list[Violation] = []
    counts_by_type: dict[ViolationType, int] = {vt: 0 for vt in ViolationType}

    if not isinstance(instance, SchedulingInstance):
        v = Violation(
            type=ViolationType.UNKNOWN_SESSION,
            session_ids=(),
            resource=None,
            day=None,
            slot=None,
            explanation="Invalid SchedulingInstance supplied to validator.",
        )
        violations.append(v)
        counts_by_type[v.type] += 1
        return ValidationReport(
            is_valid=False,
            violations=violations,
            counts_by_type=counts_by_type,
            sessions_required=0,
            sessions_assigned=0,
        )

    sessions_required = len(instance.sessions)
    inst_sessions = {s.session_id: s for s in instance.sessions}

    # 1. Normalise input into a list of (session_id, assignment) pairs
    raw_pairs: list[tuple[str, Any]] = []
    try:
        if hasattr(assignment, "assignment") and isinstance(getattr(assignment, "assignment"), Mapping):
            raw_pairs = list(getattr(assignment, "assignment").items())
        elif hasattr(assignment, "assignments") and isinstance(getattr(assignment, "assignments"), Mapping):
            raw_pairs = list(getattr(assignment, "assignments").items())
        elif isinstance(assignment, Mapping):
            raw_pairs = list(assignment.items())
        elif isinstance(assignment, Iterable):
            for item in assignment:
                if isinstance(item, tuple) and len(item) == 2:
                    raw_pairs.append((str(item[0]), item[1]))
                else:
                    violations.append(
                        Violation(
                            type=ViolationType.UNKNOWN_SESSION,
                            session_ids=(),
                            resource=None,
                            day=None,
                            slot=None,
                            explanation=f"Malformed assignment entry '{item}'.",
                        )
                    )
        else:
            violations.append(
                Violation(
                    type=ViolationType.UNKNOWN_SESSION,
                    session_ids=(),
                    resource=None,
                    day=None,
                    slot=None,
                    explanation=f"Assignment must be a Mapping or Iterable, got {type(assignment).__name__}.",
                )
            )
    except Exception as e:
        violations.append(
            Violation(
                type=ViolationType.UNKNOWN_SESSION,
                session_ids=(),
                resource=None,
                day=None,
                slot=None,
                explanation=f"Failed to inspect assignment: {e}",
            )
        )

    # Count occurrences
    id_counts = Counter(sid for sid, _ in raw_pairs)

    # DUPLICATE_SESSION
    for sid, count in id_counts.items():
        if count > 1:
            violations.append(
                Violation(
                    type=ViolationType.DUPLICATE_SESSION,
                    session_ids=(sid,),
                    resource=None,
                    day=None,
                    slot=None,
                    explanation=f"Session {sid} appears {count} times in assignment.",
                )
            )

    # UNKNOWN_SESSION
    for sid in id_counts:
        if sid not in inst_sessions:
            violations.append(
                Violation(
                    type=ViolationType.UNKNOWN_SESSION,
                    session_ids=(sid,),
                    resource=None,
                    day=None,
                    slot=None,
                    explanation=f"Session {sid} is not part of this scheduling instance.",
                )
            )

    # MISSING_SESSION
    for sid in inst_sessions:
        if sid not in id_counts:
            violations.append(
                Violation(
                    type=ViolationType.MISSING_SESSION,
                    session_ids=(sid,),
                    resource=None,
                    day=None,
                    slot=None,
                    explanation=f"Session {sid} is missing from the timetable.",
                )
            )
        else:
            # Check if all assignments for this session were None
            vals = [asgn for s, asgn in raw_pairs if s == sid]
            if all(v is None for v in vals):
                violations.append(
                    Violation(
                        type=ViolationType.MISSING_SESSION,
                        session_ids=(sid,),
                        resource=None,
                        day=None,
                        slot=None,
                        explanation=f"Session {sid} has unassigned (None) timetable slot.",
                    )
                )

    # 2. Check each assigned session individually
    valid_assigned_pairs: list[tuple[str, Assignment]] = []
    grid = instance.grid
    num_days = grid.num_days
    slots_per_day = grid.slots_per_day

    for sid, asgn in raw_pairs:
        if sid not in inst_sessions:
            continue
        if asgn is None:
            continue
        if not isinstance(asgn, Assignment):
            violations.append(
                Violation(
                    type=ViolationType.OUT_OF_RANGE,
                    session_ids=(sid,),
                    resource=None,
                    day=None,
                    slot=None,
                    explanation=f"Session {sid} assignment is not an Assignment object: {type(asgn).__name__}.",
                )
            )
            continue

        session = inst_sessions[sid]

        # UNKNOWN_ROOM
        if asgn.room_id not in instance.rooms:
            violations.append(
                Violation(
                    type=ViolationType.UNKNOWN_ROOM,
                    session_ids=(sid,),
                    resource=asgn.room_id,
                    day=asgn.day,
                    slot=asgn.start_slot,
                    explanation=f"Session {sid} assigned to unknown room '{asgn.room_id}'.",
                )
            )
            continue

        room = instance.rooms[asgn.room_id]

        # OUT_OF_RANGE
        if not (0 <= asgn.day < num_days) or not (0 <= asgn.start_slot < slots_per_day):
            violations.append(
                Violation(
                    type=ViolationType.OUT_OF_RANGE,
                    session_ids=(sid,),
                    resource=None,
                    day=asgn.day,
                    slot=asgn.start_slot,
                    explanation=f"Session {sid} day {asgn.day} or slot {asgn.start_slot} out of range (0..{num_days-1}, 0..{slots_per_day-1}).",
                )
            )
            continue

        # DURATION
        if asgn.start_slot + session.duration_slots > slots_per_day:
            violations.append(
                Violation(
                    type=ViolationType.DURATION,
                    session_ids=(sid,),
                    resource=None,
                    day=asgn.day,
                    slot=asgn.start_slot,
                    explanation=f"Session {sid} of duration {session.duration_slots} starts at slot {asgn.start_slot} and exceeds day length ({slots_per_day}).",
                )
            )

        # ROOM_TYPE
        if room.room_type not in session.room_types:
            violations.append(
                Violation(
                    type=ViolationType.ROOM_TYPE,
                    session_ids=(sid,),
                    resource=asgn.room_id,
                    day=asgn.day,
                    slot=asgn.start_slot,
                    explanation=f"Session {sid} requires room type in {session.room_types}, but room '{asgn.room_id}' is '{room.room_type}'.",
                )
            )

        # CAPACITY
        if room.capacity < session.required_capacity:
            violations.append(
                Violation(
                    type=ViolationType.CAPACITY,
                    session_ids=(sid,),
                    resource=asgn.room_id,
                    day=asgn.day,
                    slot=asgn.start_slot,
                    explanation=f"Session {sid} requires capacity {session.required_capacity}, but room '{asgn.room_id}' capacity is {room.capacity}.",
                )
            )

        # TEACHER_UNAVAILABLE & ROOM_UNAVAILABLE
        teacher = instance.teachers.get(session.teacher_id)
        max_valid_slot = min(asgn.start_slot + session.duration_slots, slots_per_day)

        if teacher:
            for s_idx in range(asgn.start_slot, max_valid_slot):
                if (asgn.day, s_idx) in teacher.unavailable:
                    label = grid.label(asgn.day, s_idx)
                    violations.append(
                        Violation(
                            type=ViolationType.TEACHER_UNAVAILABLE,
                            session_ids=(sid,),
                            resource=session.teacher_id,
                            day=asgn.day,
                            slot=s_idx,
                            explanation=f"Teacher {session.teacher_id} is unavailable for {sid} on {label}.",
                        )
                    )
                    break

        for s_idx in range(asgn.start_slot, max_valid_slot):
            if (asgn.day, s_idx) in room.unavailable:
                label = grid.label(asgn.day, s_idx)
                violations.append(
                    Violation(
                        type=ViolationType.ROOM_UNAVAILABLE,
                        session_ids=(sid,),
                        resource=asgn.room_id,
                        day=asgn.day,
                        slot=s_idx,
                        explanation=f"Room {asgn.room_id} is unavailable for {sid} on {label}.",
                    )
                )
                break

        # FIXED_ASSIGNMENT
        if session.fixed is not None and asgn != session.fixed:
            f = session.fixed
            expected = f"{grid.day_names[f.day]} {grid.slot_starts[f.start_slot]} in {f.room_id}"
            actual = f"{grid.day_names[asgn.day]} {grid.slot_starts[asgn.start_slot]} in {asgn.room_id}"
            violations.append(
                Violation(
                    type=ViolationType.FIXED_ASSIGNMENT,
                    session_ids=(sid,),
                    resource=None,
                    day=asgn.day,
                    slot=asgn.start_slot,
                    explanation=f"Session {sid} fixed at {expected}, but assigned to {actual}.",
                )
            )

        valid_assigned_pairs.append((sid, asgn))

    # 3. Conflicts (TEACHER_CONFLICT, DIVISION_CONFLICT, ROOM_CONFLICT)
    # Group sessions by (resource_kind, resource_id, day) and use interval arithmetic
    teacher_groups: dict[tuple[str, int], list[tuple[str, Assignment]]] = defaultdict(list)
    division_groups: dict[tuple[str, int], list[tuple[str, Assignment]]] = defaultdict(list)
    room_groups: dict[tuple[str, int], list[tuple[str, Assignment]]] = defaultdict(list)

    for sid, asgn in valid_assigned_pairs:
        sess = inst_sessions[sid]
        teacher_groups[(sess.teacher_id, asgn.day)].append((sid, asgn))
        division_groups[(sess.division_id, asgn.day)].append((sid, asgn))
        room_groups[(asgn.room_id, asgn.day)].append((sid, asgn))

    def _check_conflicts(
        groups: dict[tuple[str, int], list[tuple[str, Assignment]]],
        v_type: ViolationType,
        resource_desc: str,
    ):
        for (resource_id, day), session_list in groups.items():
            n = len(session_list)
            for i in range(n):
                sid1, a1 = session_list[i]
                dur1 = inst_sessions[sid1].duration_slots
                for j in range(i + 1, n):
                    sid2, a2 = session_list[j]
                    if sid1 == sid2:
                        continue  # Already caught by DUPLICATE_SESSION
                    dur2 = inst_sessions[sid2].duration_slots
                    # Interval arithmetic overlap: a1.start < a2.start + dur2 AND a2.start < a1.start + dur1
                    if a1.start_slot < a2.start_slot + dur2 and a2.start_slot < a1.start_slot + dur1:
                        conflict_slot = max(a1.start_slot, a2.start_slot)
                        day_label = (
                            grid.label(day, conflict_slot)
                            if (0 <= day < num_days and 0 <= conflict_slot < slots_per_day)
                            else f"Day {day} Slot {conflict_slot}"
                        )
                        violations.append(
                            Violation(
                                type=v_type,
                                session_ids=tuple(sorted([sid1, sid2])),
                                resource=resource_id,
                                day=day,
                                slot=conflict_slot,
                                explanation=f"{resource_desc} {resource_id} has conflict between {sid1} and {sid2} at {day_label}.",
                            )
                        )

    _check_conflicts(teacher_groups, ViolationType.TEACHER_CONFLICT, "Teacher")
    _check_conflicts(division_groups, ViolationType.DIVISION_CONFLICT, "Division")
    _check_conflicts(room_groups, ViolationType.ROOM_CONFLICT, "Room")

    # 4. Tally counts
    for v in violations:
        counts_by_type[v.type] += 1

    distinct_assigned_sessions = {sid for sid, asgn in raw_pairs if sid in inst_sessions and asgn is not None}
    sessions_assigned = len(distinct_assigned_sessions)
    is_valid = (len(violations) == 0 and sessions_assigned == sessions_required)

    return ValidationReport(
        is_valid=is_valid,
        violations=violations,
        counts_by_type=counts_by_type,
        sessions_required=sessions_required,
        sessions_assigned=sessions_assigned,
    )
