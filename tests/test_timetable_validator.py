"""Unit tests for the independent timetable validator (scheduling/timetable_validator.py)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from data.loader import load_sample, instance_from_draft
from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.session import ClassSession
from models.teacher import Teacher
from models.timeslot import TimeGrid
from scheduling.timetable_validator import (
    ViolationType,
    ValidationReport,
    validate_timetable,
)


@pytest.fixture
def tiny_instance() -> SchedulingInstance:
    draft = load_sample("tiny")
    return instance_from_draft(draft)


@pytest.fixture
def tiny_valid_solution() -> dict[str, Assignment]:
    data = json.loads(Path("tests/fixtures/tiny_solution.json").read_text(encoding="utf-8"))
    return {
        sid: Assignment(day=v[0], start_slot=v[1], room_id=v[2])
        for sid, v in data["assignments"].items()
    }


# 1. Valid case
def test_tiny_solution_is_completely_valid(tiny_instance, tiny_valid_solution):
    report = validate_timetable(tiny_instance, tiny_valid_solution)
    assert report.is_valid is True
    assert len(report.violations) == 0
    assert report.sessions_assigned == report.sessions_required == 5
    assert all(count == 0 for count in report.counts_by_type.values())


# 2. One broken test per ViolationType (14 types)

def test_violation_missing_session(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    del asgn["PLAB|A|1"]
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.MISSING_SESSION] == 1
    assert any(v.type == ViolationType.MISSING_SESSION and "PLAB|A|1" in v.session_ids for v in report.violations)

    # Missing via explicit None
    asgn_with_none = dict(tiny_valid_solution)
    asgn_with_none["PLAB|A|1"] = None
    report2 = validate_timetable(tiny_instance, asgn_with_none)
    assert report2.is_valid is False
    assert report2.counts_by_type[ViolationType.MISSING_SESSION] == 1


def test_violation_duplicate_session(tiny_instance, tiny_valid_solution):
    pairs = list(tiny_valid_solution.items())
    # Add a duplicate pair for FAI|A|2
    pairs.append(("FAI|A|2", Assignment(day=1, start_slot=2, room_id="R101")))
    report = validate_timetable(tiny_instance, pairs)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.DUPLICATE_SESSION] >= 1
    assert any(v.type == ViolationType.DUPLICATE_SESSION and "FAI|A|2" in v.session_ids for v in report.violations)


def test_violation_unknown_session(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    asgn["GHOST|SESSION|1"] = Assignment(day=0, start_slot=0, room_id="R101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.UNKNOWN_SESSION] == 1
    assert any(v.type == ViolationType.UNKNOWN_SESSION and "GHOST|SESSION|1" in v.session_ids for v in report.violations)


def test_violation_teacher_conflict(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # T01 teaches FAI|A|1 and FAI|A|2. Assign both at Mon slot 1 in different rooms
    asgn["FAI|A|2"] = Assignment(day=0, start_slot=1, room_id="R102")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.TEACHER_CONFLICT] >= 1
    v = next(v for v in report.violations if v.type == ViolationType.TEACHER_CONFLICT)
    assert v.resource == "T01"
    assert "FAI|A|1" in v.session_ids and "FAI|A|2" in v.session_ids


def test_violation_division_conflict(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # Division A attends FAI|A|1 and PLAB|A|1. Assign both at Mon slot 1
    asgn["PLAB|A|1"] = Assignment(day=0, start_slot=1, room_id="C101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.DIVISION_CONFLICT] >= 1
    v = next(v for v in report.violations if v.type == ViolationType.DIVISION_CONFLICT)
    assert v.resource == "A"


def test_violation_room_conflict(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # Assign MATH|B|1 to R101 at Mon slot 1 (where FAI|A|1 is already assigned)
    asgn["MATH|B|1"] = Assignment(day=0, start_slot=1, room_id="R101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.ROOM_CONFLICT] >= 1
    v = next(v for v in report.violations if v.type == ViolationType.ROOM_CONFLICT)
    assert v.resource == "R101"


def test_violation_capacity(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # Div A has 50 students. R102 has capacity 40. Assign FAI|A|2 to R102
    asgn["FAI|A|2"] = Assignment(day=1, start_slot=0, room_id="R102")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.CAPACITY] >= 1
    v = next(v for v in report.violations if v.type == ViolationType.CAPACITY)
    assert "FAI|A|2" in v.session_ids and v.resource == "R102"


def test_violation_room_type(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # FAI requires lecture room. Assign FAI|A|2 to C101 (computer_lab)
    asgn["FAI|A|2"] = Assignment(day=1, start_slot=0, room_id="C101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.ROOM_TYPE] >= 1
    v = next(v for v in report.violations if v.type == ViolationType.ROOM_TYPE)
    assert "FAI|A|2" in v.session_ids and v.resource == "C101"


def test_violation_teacher_unavailable(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # T01 is unavailable on Mon@09:00 (day 0, slot 0)
    asgn["FAI|A|2"] = Assignment(day=0, start_slot=0, room_id="R101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.TEACHER_UNAVAILABLE] >= 1
    v = next(v for v in report.violations if v.type == ViolationType.TEACHER_UNAVAILABLE)
    assert v.resource == "T01" and v.day == 0 and v.slot == 0


def test_violation_room_unavailable(tiny_instance, tiny_valid_solution):
    # Give R101 an unavailable slot at Tue@10:00 (day 1, slot 1)
    rooms = dict(tiny_instance.rooms)
    r101 = rooms["R101"]
    rooms["R101"] = Room(
        room_id=r101.room_id,
        name=r101.name,
        room_type=r101.room_type,
        capacity=r101.capacity,
        unavailable=frozenset({(1, 1)}),
    )
    inst = SchedulingInstance(
        name="test",
        grid=tiny_instance.grid,
        teachers=tiny_instance.teachers,
        rooms=rooms,
        divisions=tiny_instance.divisions,
        courses=tiny_instance.courses,
        sessions=tiny_instance.sessions,
        meta=tiny_instance.meta,
    )
    # In tiny solution, MATH|A|1 is at (1, 1, R101)
    report = validate_timetable(inst, tiny_valid_solution)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.ROOM_UNAVAILABLE] == 1


def test_violation_duration(tiny_instance):
    # Create a 2-slot course
    c_lab = Course(
        course_id="CLAB",
        name="Computer Lab",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=2,
        room_types=("computer_lab",),
        eligible_divisions=("A",),
    )
    courses = dict(tiny_instance.courses)
    courses["CLAB"] = c_lab
    divs = dict(tiny_instance.divisions)
    divs["A"] = Division(division_id="A", name="Div A", student_count=50, enrolled_courses=("CLAB",))
    sessions = expand_sessions(courses, divs)
    inst = SchedulingInstance(
        name="test",
        grid=tiny_instance.grid,
        teachers=tiny_instance.teachers,
        rooms=tiny_instance.rooms,
        divisions=divs,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    # Grid has 3 slots: 0, 1, 2. Starting a 2-slot session at slot 2 overflows!
    asgn = {"CLAB|A|1": Assignment(day=0, start_slot=2, room_id="C101")}
    report = validate_timetable(inst, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.DURATION] == 1


def test_violation_out_of_range(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # Grid has 2 days (0, 1) and 3 slots (0, 1, 2). Put day=9, slot=99
    asgn["FAI|A|2"] = Assignment(day=9, start_slot=99, room_id="R101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.OUT_OF_RANGE] == 1


def test_violation_unknown_room(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    asgn["FAI|A|2"] = Assignment(day=1, start_slot=0, room_id="R999")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.UNKNOWN_ROOM] == 1


def test_violation_fixed_assignment(tiny_instance, tiny_valid_solution):
    asgn = dict(tiny_valid_solution)
    # FAI|A|1 is fixed at Mon@10:00 in R101 (0, 1, R101)
    # Move it to Mon@11:00 (0, 2, R101)
    asgn["FAI|A|1"] = Assignment(day=0, start_slot=2, room_id="R101")
    report = validate_timetable(tiny_instance, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.FIXED_ASSIGNMENT] == 1


# 3. Touching intervals vs overlapping intervals

def test_touching_intervals_not_a_conflict(tiny_instance):
    # Two sessions in R101: Session 1 at [0, 1), Session 2 at [1, 2)
    # Same room, different sessions, same day
    # Touching intervals [0, 1) and [1, 2) must NOT conflict!
    s1 = ClassSession(
        session_id="S1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
    )
    s2 = ClassSession(
        session_id="S2",
        course_id="MATH",
        division_id="B",
        teacher_id="T02",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=25,
    )
    inst = SchedulingInstance(
        name="test",
        grid=tiny_instance.grid,
        teachers=tiny_instance.teachers,
        rooms=tiny_instance.rooms,
        divisions=tiny_instance.divisions,
        courses=tiny_instance.courses,
        sessions=(s1, s2),
        meta={},
    )
    asgn = {
        "S1": Assignment(day=1, start_slot=0, room_id="R101"),
        "S2": Assignment(day=1, start_slot=1, room_id="R101"),
    }
    report = validate_timetable(inst, asgn)
    assert report.is_valid is True
    assert report.counts_by_type[ViolationType.ROOM_CONFLICT] == 0


def test_two_slot_overlap_detected(tiny_instance):
    # S1 has duration 2 at [0, 2). S2 has duration 1 at [1, 2).
    # Both in R101 -> Overlap at slot 1 must be detected!
    s1 = ClassSession(
        session_id="S1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=2,
        room_types=("lecture",),
        required_capacity=50,
    )
    s2 = ClassSession(
        session_id="S2",
        course_id="MATH",
        division_id="B",
        teacher_id="T02",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=25,
    )
    inst = SchedulingInstance(
        name="test",
        grid=tiny_instance.grid,
        teachers=tiny_instance.teachers,
        rooms=tiny_instance.rooms,
        divisions=tiny_instance.divisions,
        courses=tiny_instance.courses,
        sessions=(s1, s2),
        meta={},
    )
    asgn = {
        "S1": Assignment(day=1, start_slot=0, room_id="R101"),
        "S2": Assignment(day=1, start_slot=1, room_id="R101"),
    }
    report = validate_timetable(inst, asgn)
    assert report.is_valid is False
    assert report.counts_by_type[ViolationType.ROOM_CONFLICT] == 1


# 4. Garbage input robustness

def test_garbage_input_does_not_raise(tiny_instance):
    # None
    rep = validate_timetable(tiny_instance, None)
    assert rep.is_valid is False

    # Empty dict
    rep2 = validate_timetable(tiny_instance, {})
    assert rep2.is_valid is False

    # Malformed list
    rep3 = validate_timetable(tiny_instance, [1, 2, "not a tuple"])
    assert rep3.is_valid is False

    # Bad object for instance
    rep4 = validate_timetable("Not an instance", {})
    assert rep4.is_valid is False
