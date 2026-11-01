"""SchedulingInstance representation and session expansion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.room import Room
from models.session import ClassSession
from models.teacher import Teacher
from models.timeslot import TimeGrid

ROOM_TYPES: tuple[str, ...] = ("lecture", "computer_lab", "general_lab")


@dataclass(frozen=True)
class SchedulingInstance:
    """Complete scheduling problem instance."""

    name: str
    grid: TimeGrid
    teachers: dict[str, Teacher]
    rooms: dict[str, Room]
    divisions: dict[str, Division]
    courses: dict[str, Course]
    sessions: tuple[ClassSession, ...]
    meta: dict


def expand_sessions(
    courses: Mapping[str, Course],
    divisions: Mapping[str, Division],
    fixed: Mapping[str, Assignment] | None = None,
) -> tuple[ClassSession, ...]:
    """For every division d and course c with c in d.enrolled_courses AND d in c.eligible_divisions,
    create c.sessions_per_week sessions numbered 1..n. Sort result by session_id."""
    fixed_map = fixed or {}
    generated: list[ClassSession] = []

    for div_id, division in divisions.items():
        for course_id in division.enrolled_courses:
            if course_id in courses:
                course = courses[course_id]
                if div_id in course.eligible_divisions:
                    for n in range(1, course.sessions_per_week + 1):
                        sid = f"{course_id}|{div_id}|{n}"
                        sess = ClassSession(
                            session_id=sid,
                            course_id=course_id,
                            division_id=div_id,
                            teacher_id=course.teacher_id,
                            duration_slots=course.duration_slots,
                            room_types=course.room_types,
                            required_capacity=division.student_count,
                            fixed=fixed_map.get(sid),
                        )
                        generated.append(sess)

    generated.sort(key=lambda s: s.session_id)
    return tuple(generated)
