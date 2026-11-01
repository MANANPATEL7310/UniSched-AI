"""Input validation for SchedulingInstance before CSP search."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from data.schemas import ROOM_TYPES
from models.instance import SchedulingInstance


@dataclass(frozen=True)
class InputIssue:
    """An issue identified during input validation before scheduling search starts."""

    severity: str  # "ERROR" | "WARNING"
    code: str
    message: str
    entity: str | None = None


def validate_instance(inst: SchedulingInstance) -> list[InputIssue]:
    """Validate a SchedulingInstance and return a list of ERROR and WARNING issues.
    
    Search must not start while any issue with severity == "ERROR" exists.
    """
    issues: list[InputIssue] = []

    # 1. Grid structure
    if inst.grid.num_days == 0:
        issues.append(InputIssue(severity="ERROR", code="NO_DAYS", message="No days defined.", entity=None))
    if inst.grid.slots_per_day == 0:
        issues.append(InputIssue(severity="ERROR", code="NO_SLOTS", message="No slots defined.", entity=None))

    # 2. Sessions
    if len(inst.sessions) == 0:
        issues.append(
            InputIssue(
                severity="ERROR",
                code="NO_SESSIONS",
                message="No sessions to schedule. Check course/division enrolment.",
                entity=None,
            )
        )

    # 3. Referencing integrity & courses
    for course_id, course in inst.courses.items():
        if course.teacher_id not in inst.teachers:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="UNKNOWN_TEACHER",
                    message=f"Course {course_id} uses unknown teacher {course.teacher_id}.",
                    entity=f"course:{course_id}",
                )
            )

        for div_id in course.eligible_divisions:
            if div_id not in inst.divisions:
                issues.append(
                    InputIssue(
                        severity="ERROR",
                        code="UNKNOWN_DIVISION",
                        message=f"Course {course_id} is eligible for unknown division {div_id}.",
                        entity=f"course:{course_id}",
                    )
                )

        # BAD_DURATION
        s_per_day = inst.grid.slots_per_day
        if course.duration_slots < 1:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="BAD_DURATION",
                    message=f"Course {course_id}: duration {course.duration_slots} must be at least 1 slot.",
                    entity=f"course:{course_id}",
                )
            )
        elif s_per_day > 0 and course.duration_slots > s_per_day:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="BAD_DURATION",
                    message=f"Course {course_id}: duration {course.duration_slots} exceeds {s_per_day} slots per day.",
                    entity=f"course:{course_id}",
                )
            )

        # BAD_SESSIONS_PER_WEEK
        if course.sessions_per_week < 1:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="BAD_SESSIONS_PER_WEEK",
                    message=f"Course {course_id}: sessions_per_week must be at least 1.",
                    entity=f"course:{course_id}",
                )
            )

        # BAD_ROOM_TYPE for course
        for rt in course.room_types:
            if rt not in ROOM_TYPES:
                issues.append(
                    InputIssue(
                        severity="ERROR",
                        code="BAD_ROOM_TYPE",
                        message=f"Course {course_id} requires invalid room type '{rt}'.",
                        entity=f"course:{course_id}",
                    )
                )

        # NO_ROOM_TYPE_MATCH
        available_room_types = {r.room_type for r in inst.rooms.values()}
        if not any(rt in available_room_types for rt in course.room_types):
            types_str = ", ".join(course.room_types)
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="NO_ROOM_TYPE_MATCH",
                    message=f"No room of type {types_str} exists for {course_id}.",
                    entity=f"course:{course_id}",
                )
            )

    # 4. Divisions
    for div_id, division in inst.divisions.items():
        if division.student_count <= 0:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="BAD_CAPACITY",
                    message=f"Division {div_id}: student_count must be greater than 0.",
                    entity=f"division:{div_id}",
                )
            )

        for c_id in division.enrolled_courses:
            if c_id not in inst.courses:
                issues.append(
                    InputIssue(
                        severity="ERROR",
                        code="UNKNOWN_COURSE",
                        message=f"Division {div_id} enrols unknown course {c_id}.",
                        entity=f"division:{div_id}",
                    )
                )

    # 5. ALLOCATION_MISMATCH (Cross-check between course and division)
    for div_id, division in inst.divisions.items():
        for c_id in division.enrolled_courses:
            if c_id in inst.courses:
                if div_id not in inst.courses[c_id].eligible_divisions:
                    issues.append(
                        InputIssue(
                            severity="ERROR",
                            code="ALLOCATION_MISMATCH",
                            message=f"Division {div_id} enrols {c_id} but {c_id} is not eligible for {div_id}.",
                            entity=f"division:{div_id}",
                        )
                    )

    for c_id, course in inst.courses.items():
        for div_id in course.eligible_divisions:
            if div_id in inst.divisions:
                if c_id not in inst.divisions[div_id].enrolled_courses:
                    issues.append(
                        InputIssue(
                            severity="ERROR",
                            code="ALLOCATION_MISMATCH",
                            message=f"Course {c_id} is eligible for {div_id} but {div_id} does not enrol {c_id}.",
                            entity=f"course:{c_id}",
                        )
                    )

    # 6. Rooms
    for room_id, room in inst.rooms.items():
        if room.room_type not in ROOM_TYPES:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="BAD_ROOM_TYPE",
                    message=f"Room {room_id} has invalid room type '{room.room_type}'.",
                    entity=f"room:{room_id}",
                )
            )
        if room.capacity <= 0:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="BAD_CAPACITY",
                    message=f"Room {room_id}: capacity must be greater than 0.",
                    entity=f"room:{room_id}",
                )
            )

    # 7. Session fit in rooms (NO_ROOM_BIG_ENOUGH)
    reported_pairs: set[tuple[str, str]] = set()
    for sess in inst.sessions:
        pair = (sess.course_id, sess.division_id)
        if pair in reported_pairs:
            continue
        fits_any = any(
            r.room_type in sess.room_types and r.capacity >= sess.required_capacity
            for r in inst.rooms.values()
        )
        if not fits_any:
            reported_pairs.add(pair)
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="NO_ROOM_BIG_ENOUGH",
                    message=f"Division {sess.division_id} ({sess.required_capacity} students) fits no permitted room for {sess.course_id}.",
                    entity=f"session:{sess.session_id}",
                )
            )

    # 8. Fixed assignments validation
    session_ids = {s.session_id for s in inst.sessions}
    fixed_session_ids = inst.meta.get("fixed_session_ids", ())
    for sid in fixed_session_ids:
        if sid not in session_ids:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="FIXED_UNKNOWN_SESSION",
                    message=f"Fixed assignment references unknown session {sid}.",
                    entity=f"session:{sid}",
                )
            )

    fixed_sessions = [s for s in inst.sessions if s.fixed is not None]
    for s in fixed_sessions:
        f = s.fixed
        assert f is not None
        # Room exists
        if f.room_id not in inst.rooms:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="FIXED_INVALID",
                    message=f"Fixed assignment for {s.session_id} is not allowed: room {f.room_id} does not exist.",
                    entity=f"session:{s.session_id}",
                )
            )
            continue

        room = inst.rooms[f.room_id]
        # Room type permitted
        if room.room_type not in s.room_types:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="FIXED_INVALID",
                    message=f"Fixed assignment for {s.session_id} is not allowed: room type '{room.room_type}' not permitted.",
                    entity=f"session:{s.session_id}",
                )
            )

        # Capacity permitted
        if room.capacity < s.required_capacity:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="FIXED_INVALID",
                    message=f"Fixed assignment for {s.session_id} is not allowed: room capacity {room.capacity} < required {s.required_capacity}.",
                    entity=f"session:{s.session_id}",
                )
            )

        # Bounds and duration
        if f.day < 0 or f.day >= inst.grid.num_days:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="FIXED_INVALID",
                    message=f"Fixed assignment for {s.session_id} is not allowed: day {f.day} out of range.",
                    entity=f"session:{s.session_id}",
                )
            )
        elif f.start_slot < 0 or f.start_slot + s.duration_slots > inst.grid.slots_per_day:
            issues.append(
                InputIssue(
                    severity="ERROR",
                    code="FIXED_INVALID",
                    message=f"Fixed assignment for {s.session_id} is not allowed: slot {f.start_slot} + duration {s.duration_slots} exceeds day slots.",
                    entity=f"session:{s.session_id}",
                )
            )
        else:
            # Availability checks
            teacher = inst.teachers.get(s.teacher_id)
            for slot in range(f.start_slot, f.start_slot + s.duration_slots):
                if teacher and (f.day, slot) in teacher.unavailable:
                    issues.append(
                        InputIssue(
                            severity="ERROR",
                            code="FIXED_INVALID",
                            message=f"Fixed assignment for {s.session_id} is not allowed: teacher unavailable.",
                            entity=f"session:{s.session_id}",
                        )
                    )
                    break

            for slot in range(f.start_slot, f.start_slot + s.duration_slots):
                if (f.day, slot) in room.unavailable:
                    issues.append(
                        InputIssue(
                            severity="ERROR",
                            code="FIXED_INVALID",
                            message=f"Fixed assignment for {s.session_id} is not allowed: room unavailable.",
                            entity=f"session:{s.session_id}",
                        )
                    )
                    break

    # 9. Fixed clashes
    for i in range(len(fixed_sessions)):
        for j in range(i + 1, len(fixed_sessions)):
            s1 = fixed_sessions[i]
            s2 = fixed_sessions[j]
            f1 = s1.fixed
            f2 = s2.fixed
            assert f1 is not None and f2 is not None
            if f1.day == f2.day:
                # Interval overlap: a.start < b.start + b.dur and b.start < a.start + a.dur
                if f1.start_slot < f2.start_slot + s2.duration_slots and f2.start_slot < f1.start_slot + s1.duration_slots:
                    if s1.teacher_id == s2.teacher_id:
                        issues.append(
                            InputIssue(
                                severity="ERROR",
                                code="FIXED_CLASH",
                                message=f"Fixed assignments clash: teacher {s1.teacher_id} assigned to both {s1.session_id} and {s2.session_id} at the same time.",
                                entity=f"teacher:{s1.teacher_id}",
                            )
                        )
                    if s1.division_id == s2.division_id:
                        issues.append(
                            InputIssue(
                                severity="ERROR",
                                code="FIXED_CLASH",
                                message=f"Fixed assignments clash: division {s1.division_id} assigned to both {s1.session_id} and {s2.session_id} at the same time.",
                                entity=f"division:{s1.division_id}",
                            )
                        )
                    if f1.room_id == f2.room_id:
                        issues.append(
                            InputIssue(
                                severity="ERROR",
                                code="FIXED_CLASH",
                                message=f"Fixed assignments clash: room {f1.room_id} assigned to both {s1.session_id} and {s2.session_id} at the same time.",
                                entity=f"room:{f1.room_id}",
                            )
                        )

    # 10. WARNINGS
    total_slots = inst.grid.num_days * inst.grid.slots_per_day

    # TEACHER_OVERLOAD
    for t_id, teacher in inst.teachers.items():
        needed_slots = sum(s.duration_slots for s in inst.sessions if s.teacher_id == t_id)
        avail_slots = total_slots - len(teacher.unavailable)
        if needed_slots > avail_slots:
            issues.append(
                InputIssue(
                    severity="WARNING",
                    code="TEACHER_OVERLOAD",
                    message=f"Teacher {t_id} needs {needed_slots} slots but is available in only {avail_slots}.",
                    entity=f"teacher:{t_id}",
                )
            )

    # DIVISION_OVERLOAD
    for div_id, division in inst.divisions.items():
        needed_slots = sum(s.duration_slots for s in inst.sessions if s.division_id == div_id)
        if needed_slots > total_slots:
            issues.append(
                InputIssue(
                    severity="WARNING",
                    code="DIVISION_OVERLOAD",
                    message=f"Division {div_id} needs {needed_slots} slots but grid has only {total_slots} total weekly slots.",
                    entity=f"division:{div_id}",
                )
            )

    # ROOM_TYPE_OVERLOAD
    for rt in ROOM_TYPES:
        rooms_of_type = [r for r in inst.rooms.values() if r.room_type == rt]
        type_capacity_slots = len(rooms_of_type) * total_slots
        # Sessions that require exclusively this room type
        needed_type_slots = sum(
            s.duration_slots for s in inst.sessions if s.room_types == (rt,)
        )
        if needed_type_slots > type_capacity_slots:
            issues.append(
                InputIssue(
                    severity="WARNING",
                    code="ROOM_TYPE_OVERLOAD",
                    message=f"Total required slots ({needed_type_slots}) for room type '{rt}' exceeds capacity ({type_capacity_slots}).",
                    entity=f"room_type:{rt}",
                )
            )

    # TEACHER_DAILY_MAX
    for t_id, teacher in inst.teachers.items():
        if teacher.max_daily_sessions is not None:
            sess_count = sum(1 for s in inst.sessions if s.teacher_id == t_id)
            max_sessions_allowed = teacher.max_daily_sessions * inst.grid.num_days
            if sess_count > max_sessions_allowed:
                issues.append(
                    InputIssue(
                        severity="WARNING",
                        code="TEACHER_DAILY_MAX",
                        message=f"Teacher {t_id}: {sess_count} sessions exceeds maximum weekly allowance of {max_sessions_allowed}.",
                        entity=f"teacher:{t_id}",
                    )
                )

    # EXTRA_COLUMN warning if recorded in meta
    if "extra_columns" in inst.meta:
        for extra in inst.meta["extra_columns"]:
            issues.append(
                InputIssue(
                    severity="WARNING",
                    code="EXTRA_COLUMN",
                    message=f"Extra column ignored: {extra}",
                    entity=None,
                )
            )

    return issues
