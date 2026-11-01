"""Unit tests for the input validator (data/validator.py), covering each issue code."""
from __future__ import annotations

import copy
import pytest

from data.loader import load_sample, instance_from_draft
from data.validator import validate_instance, InputIssue
from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.session import ClassSession
from models.teacher import Teacher
from models.timeslot import TimeGrid


@pytest.fixture
def valid_tiny_instance() -> SchedulingInstance:
    draft = load_sample("tiny")
    return instance_from_draft(draft)


def test_valid_instance_has_no_errors(valid_tiny_instance):
    issues = validate_instance(valid_tiny_instance)
    errors = [i for i in issues if i.severity == "ERROR"]
    assert len(errors) == 0


def test_no_days(valid_tiny_instance):
    empty_grid = TimeGrid(day_names=(), slot_starts=valid_tiny_instance.grid.slot_starts, slot_ends=valid_tiny_instance.grid.slot_ends)
    inst = SchedulingInstance(
        name=valid_tiny_instance.name,
        grid=empty_grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta=valid_tiny_instance.meta,
    )
    issues = validate_instance(inst)
    assert any(i.code == "NO_DAYS" for i in issues)


def test_no_slots(valid_tiny_instance):
    empty_grid = TimeGrid(day_names=valid_tiny_instance.grid.day_names, slot_starts=(), slot_ends=())
    inst = SchedulingInstance(
        name=valid_tiny_instance.name,
        grid=empty_grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta=valid_tiny_instance.meta,
    )
    issues = validate_instance(inst)
    assert any(i.code == "NO_SLOTS" for i in issues)


def test_no_sessions(valid_tiny_instance):
    inst = SchedulingInstance(
        name=valid_tiny_instance.name,
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=(),
        meta=valid_tiny_instance.meta,
    )
    issues = validate_instance(inst)
    assert any(i.code == "NO_SESSIONS" for i in issues)


def test_unknown_teacher(valid_tiny_instance):
    bad_course = Course(
        course_id="BIO",
        name="Biology",
        teacher_id="T999",  # Non-existent
        sessions_per_week=1,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["BIO"] = bad_course
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "UNKNOWN_TEACHER" and "T999" in i.message for i in issues)


def test_unknown_division(valid_tiny_instance):
    bad_course = Course(
        course_id="BIO",
        name="Biology",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("UNKNOWN_DIV",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["BIO"] = bad_course
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "UNKNOWN_DIVISION" and "UNKNOWN_DIV" in i.message for i in issues)


def test_unknown_course(valid_tiny_instance):
    bad_div = Division(
        division_id="DIV_X",
        name="Div X",
        student_count=30,
        enrolled_courses=("NONEXISTENT_COURSE",),
    )
    divs = dict(valid_tiny_instance.divisions)
    divs["DIV_X"] = bad_div
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=divs,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "UNKNOWN_COURSE" and "NONEXISTENT_COURSE" in i.message for i in issues)


def test_allocation_mismatch(valid_tiny_instance):
    # Div A enrols FAI, but let's remove Div A from FAI's eligible divisions
    course = valid_tiny_instance.courses["FAI"]
    mismatched_course = Course(
        course_id=course.course_id,
        name=course.name,
        teacher_id=course.teacher_id,
        sessions_per_week=course.sessions_per_week,
        duration_slots=course.duration_slots,
        room_types=course.room_types,
        eligible_divisions=(),  # Mismatch: A enrols FAI, but FAI not eligible for A
    )
    courses = dict(valid_tiny_instance.courses)
    courses["FAI"] = mismatched_course
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "ALLOCATION_MISMATCH" for i in issues)


def test_bad_room_type(valid_tiny_instance):
    bad_room = Room(room_id="R_BAD", name="Bad", room_type="sports_arena", capacity=50)
    rooms = dict(valid_tiny_instance.rooms)
    rooms["R_BAD"] = bad_room

    bad_course = Course(
        course_id="GYM",
        name="Gym",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("sports_arena",),
        eligible_divisions=("A",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["GYM"] = bad_course

    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    room_issues = [i for i in issues if i.code == "BAD_ROOM_TYPE"]
    assert len(room_issues) >= 2


def test_bad_duration(valid_tiny_instance):
    # Duration > slots_per_day (slots_per_day = 3 in tiny)
    bad_course = Course(
        course_id="LONG",
        name="Long",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=5,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["LONG"] = bad_course

    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "BAD_DURATION" and "exceeds" in i.message for i in issues)

    # Duration < 1
    zero_course = Course(
        course_id="ZERO",
        name="Zero",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=0,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    courses["ZERO"] = zero_course
    inst2 = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues2 = validate_instance(inst2)
    assert any(i.code == "BAD_DURATION" and "at least 1" in i.message for i in issues2)


def test_bad_sessions_per_week(valid_tiny_instance):
    bad_course = Course(
        course_id="NO_FREQ",
        name="No Freq",
        teacher_id="T01",
        sessions_per_week=0,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["NO_FREQ"] = bad_course
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "BAD_SESSIONS_PER_WEEK" for i in issues)


def test_bad_capacity(valid_tiny_instance):
    bad_room = Room(room_id="R_NEG", name="Neg", room_type="lecture", capacity=0)
    rooms = dict(valid_tiny_instance.rooms)
    rooms["R_NEG"] = bad_room

    bad_div = Division(division_id="D_NEG", name="Neg", student_count=-5, enrolled_courses=())
    divs = dict(valid_tiny_instance.divisions)
    divs["D_NEG"] = bad_div

    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=rooms,
        divisions=divs,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    cap_issues = [i for i in issues if i.code == "BAD_CAPACITY"]
    assert len(cap_issues) == 2


def test_no_room_type_match(valid_tiny_instance):
    # Course needs general_lab, but tiny rooms are only lecture and computer_lab
    chem = Course(
        course_id="CHEM",
        name="Chemistry",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("general_lab",),
        eligible_divisions=("A",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["CHEM"] = chem
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "NO_ROOM_TYPE_MATCH" and "general_lab" in i.message for i in issues)


def test_no_room_big_enough(valid_tiny_instance):
    # Division A has 50 students. If all rooms have max capacity 30:
    small_rooms = {
        r_id: Room(room_id=r.room_id, name=r.name, room_type=r.room_type, capacity=30, unavailable=r.unavailable)
        for r_id, r in valid_tiny_instance.rooms.items()
    }
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=small_rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "NO_ROOM_BIG_ENOUGH" and "Division A" in i.message for i in issues)


def test_fixed_unknown_session(valid_tiny_instance):
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={"fixed_session_ids": ("NON_EXISTENT_SESSION",)},
    )
    issues = validate_instance(inst)
    assert any(i.code == "FIXED_UNKNOWN_SESSION" for i in issues)


def test_fixed_invalid_teacher_unavailable(valid_tiny_instance):
    # Teacher T01 is unavailable at Mon@09:00 (day 0, slot 0)
    # Fix FAI|A|1 at Mon@09:00
    fixed_sess = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
        fixed=Assignment(day=0, start_slot=0, room_id="R101"),
    )
    other_sessions = [s for s in valid_tiny_instance.sessions if s.session_id != "FAI|A|1"]
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=(fixed_sess,) + tuple(other_sessions),
        meta={"fixed_session_ids": ("FAI|A|1",)},
    )
    issues = validate_instance(inst)
    assert any(i.code == "FIXED_INVALID" and "teacher unavailable" in i.message for i in issues)


def test_fixed_clash(valid_tiny_instance):
    # Two sessions fixed at the exact same time and room
    f1 = Assignment(day=1, start_slot=0, room_id="R101")
    f2 = Assignment(day=1, start_slot=0, room_id="R101")

    s1 = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
        fixed=f1,
    )
    s2 = ClassSession(
        session_id="MATH|B|1",
        course_id="MATH",
        division_id="B",
        teacher_id="T02",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=25,
        fixed=f2,
    )
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=(s1, s2),
        meta={"fixed_session_ids": ("FAI|A|1", "MATH|B|1")},
    )
    issues = validate_instance(inst)
    assert any(i.code == "FIXED_CLASH" and "room R101" in i.message for i in issues)


def test_teacher_overload_warning(valid_tiny_instance):
    # Grid is 2 days x 3 slots = 6 total slots.
    # Make T01 unavailable for 5 slots. Then T01 has 1 available slot, but FAI needs 2 slots.
    t01 = Teacher(
        teacher_id="T01",
        name="Dr. Rao",
        unavailable=frozenset({(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)}),
    )
    teachers = dict(valid_tiny_instance.teachers)
    teachers["T01"] = t01
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "TEACHER_OVERLOAD" and i.severity == "WARNING" for i in issues)


def test_division_overload_warning(valid_tiny_instance):
    # Total weekly slots = 6. Let Div A need 10 slots.
    heavy_course = Course(
        course_id="HEAVY",
        name="Heavy",
        teacher_id="T01",
        sessions_per_week=10,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    div_a = Division(
        division_id="A",
        name="Div A",
        student_count=50,
        enrolled_courses=("HEAVY",),
    )
    divs = dict(valid_tiny_instance.divisions)
    divs["A"] = div_a
    courses = dict(valid_tiny_instance.courses)
    courses["HEAVY"] = heavy_course
    sessions = expand_sessions(courses, divs)
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=divs,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "DIVISION_OVERLOAD" and i.severity == "WARNING" for i in issues)


def test_room_type_overload_warning(valid_tiny_instance):
    # In tiny, C101 is the only computer_lab. Total slots for computer_lab = 1 x 6 = 6.
    # If lab courses need 10 slots:
    lab_course = Course(
        course_id="LAB10",
        name="Lab 10",
        teacher_id="T03",
        sessions_per_week=10,
        duration_slots=1,
        room_types=("computer_lab",),
        eligible_divisions=("A",),
    )
    courses = dict(valid_tiny_instance.courses)
    courses["LAB10"] = lab_course
    divs = dict(valid_tiny_instance.divisions)
    divs["A"] = Division(division_id="A", name="Div A", student_count=50, enrolled_courses=("LAB10",))
    sessions = expand_sessions(courses, divs)
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=divs,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "ROOM_TYPE_OVERLOAD" and i.severity == "WARNING" for i in issues)


def test_teacher_daily_max_warning(valid_tiny_instance):
    # T01 has 2 sessions in tiny (FAI|A|1 and FAI|A|2).
    # If max_daily_sessions=0, total allowed across 2 days is 0 < 2 sessions:
    t01 = Teacher(
        teacher_id="T01",
        name="Dr. Rao",
        unavailable=frozenset(),
        max_daily_sessions=0,
    )
    teachers = dict(valid_tiny_instance.teachers)
    teachers["T01"] = t01
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={},
    )
    issues = validate_instance(inst)
    assert any(i.code == "TEACHER_DAILY_MAX" and i.severity == "WARNING" for i in issues)


def test_extra_column_warning(valid_tiny_instance):
    inst = SchedulingInstance(
        name="test",
        grid=valid_tiny_instance.grid,
        teachers=valid_tiny_instance.teachers,
        rooms=valid_tiny_instance.rooms,
        divisions=valid_tiny_instance.divisions,
        courses=valid_tiny_instance.courses,
        sessions=valid_tiny_instance.sessions,
        meta={"extra_columns": ["notes_col"]},
    )
    issues = validate_instance(inst)
    assert any(i.code == "EXTRA_COLUMN" and i.severity == "WARNING" for i in issues)
