"""Unit tests for CSP domain generation and problem compilation."""
from __future__ import annotations

import pytest

from csp.constraints import occupancy_keys
from csp.domains import build_domains
from csp.problem import CSPProblem, build_csp
from models import (
    Assignment,
    ClassSession,
    Course,
    Division,
    Room,
    SchedulingInstance,
    Teacher,
    TimeGrid,
    expand_sessions,
)


@pytest.fixture
def tiny_instance() -> SchedulingInstance:
    grid = TimeGrid(
        day_names=("Mon", "Tue"),
        slot_starts=("09:00", "10:00", "11:00"),
        slot_ends=("10:00", "11:00", "12:00"),
    )
    teachers = {
        "T01": Teacher(
            teacher_id="T01",
            name="Dr. Rao",
            unavailable=frozenset([(0, 0)]),  # Mon@09:00
        ),
        "T02": Teacher(teacher_id="T02", name="Dr. Sharma"),
        "T03": Teacher(teacher_id="T03", name="Prof. Lee"),
    }
    rooms = {
        "R101": Room(room_id="R101", name="Room 101", room_type="lecture", capacity=60),
        "R102": Room(room_id="R102", name="Room 102", room_type="lecture", capacity=40),
        "C101": Room(room_id="C101", name="Lab 101", room_type="computer_lab", capacity=60),
    }
    divisions = {
        "A": Division(
            division_id="A",
            name="Division A",
            student_count=50,
            enrolled_courses=("FAI", "MATH", "PLAB"),
        ),
        "B": Division(
            division_id="B",
            name="Division B",
            student_count=25,
            enrolled_courses=("MATH",),
        ),
    }
    courses = {
        "FAI": Course(
            course_id="FAI",
            name="Foundation of AI",
            teacher_id="T01",
            sessions_per_week=2,
            duration_slots=1,
            room_types=("lecture",),
            eligible_divisions=("A",),
        ),
        "MATH": Course(
            course_id="MATH",
            name="Discrete Math",
            teacher_id="T02",
            sessions_per_week=1,
            duration_slots=1,
            room_types=("lecture",),
            eligible_divisions=("A", "B"),
        ),
        "PLAB": Course(
            course_id="PLAB",
            name="Python Lab",
            teacher_id="T03",
            sessions_per_week=1,
            duration_slots=1,
            room_types=("computer_lab",),
            eligible_divisions=("A",),
        ),
    }
    fixed = {
        "FAI|A|1": Assignment(day=0, start_slot=1, room_id="R101"),
    }
    sessions = expand_sessions(courses, divisions, fixed)
    return SchedulingInstance(
        name="tiny",
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=sessions,
        meta={"source": "test"},
    )


def test_tiny_domain_sizes_hand_verified(tiny_instance: SchedulingInstance):
    domains = build_domains(tiny_instance)
    assert len(domains) == 5

    # Hand-verified counts:
    # FAI|A|1: fixed at Mon 10:00 R101 -> 1
    assert len(domains["FAI|A|1"]) == 1
    assert domains["FAI|A|1"][0] == Assignment(day=0, start_slot=1, room_id="R101")

    # FAI|A|2: T01 free in 5 slots, only R101 has capacity 60 >= 50 and type lecture -> 5
    assert len(domains["FAI|A|2"]) == 5
    for a in domains["FAI|A|2"]:
        assert a.room_id == "R101"
        assert not (a.day == 0 and a.start_slot == 0)

    # MATH|A|1: T02 has 6 slots, only R101 fits A (50 students) -> 6
    assert len(domains["MATH|A|1"]) == 6
    for a in domains["MATH|A|1"]:
        assert a.room_id == "R101"

    # MATH|B|1: T02 has 6 slots, B has 25 students (fits R101 and R102) -> 6 * 2 = 12
    assert len(domains["MATH|B|1"]) == 12
    r101_count = sum(1 for a in domains["MATH|B|1"] if a.room_id == "R101")
    r102_count = sum(1 for a in domains["MATH|B|1"] if a.room_id == "R102")
    assert r101_count == 6
    assert r102_count == 6

    # PLAB|A|1: T03 has 6 slots, only C101 has computer_lab and cap 60 >= 50 -> 6
    assert len(domains["PLAB|A|1"]) == 6
    for a in domains["PLAB|A|1"]:
        assert a.room_id == "C101"


def test_build_csp_properties(tiny_instance: SchedulingInstance):
    problem = build_csp(tiny_instance)

    assert problem.variables == (
        "FAI|A|1",
        "FAI|A|2",
        "MATH|A|1",
        "MATH|B|1",
        "PLAB|A|1",
    )
    assert problem.slots_per_day == 3
    assert problem.root_wipeout is None

    # Keys structure
    for s in problem.variables:
        assert len(problem.keys[s]) == len(problem.domains[s])
        for ks in problem.keys[s]:
            assert len(ks) == 3  # All 1-slot sessions: 3 keys each

    # Neighbors must be symmetric and irreflexive
    for s1 in problem.variables:
        assert s1 not in problem.neighbors[s1]
        for s2 in problem.neighbors[s1]:
            assert s1 in problem.neighbors[s2]

    # FAI|A|1 and FAI|A|2 share teacher T01 and division A -> must be neighbors
    assert "FAI|A|2" in problem.neighbors["FAI|A|1"]
    # MATH|A|1 and MATH|B|1 share teacher T02 -> must be neighbors
    assert "MATH|B|1" in problem.neighbors["MATH|A|1"]


def test_conflicts_detection(tiny_instance: SchedulingInstance):
    problem = build_csp(tiny_instance)

    # In tiny, FAI|A|1 only has 1 value: Mon slot 1 in R101.
    # Find value index for FAI|A|2 that places it also in Mon slot 1 in R101.
    fai2_domain = problem.domains["FAI|A|2"]
    clash_idx = fai2_domain.index(Assignment(day=0, start_slot=1, room_id="R101"))
    assert problem.conflicts("FAI|A|1", 0, "FAI|A|2", clash_idx) is True

    # Find value index for FAI|A|2 at Tue slot 0 in R101 (different day)
    non_clash_idx = fai2_domain.index(Assignment(day=1, start_slot=0, room_id="R101"))
    assert problem.conflicts("FAI|A|1", 0, "FAI|A|2", non_clash_idx) is False


def test_root_wipeout_detected():
    # Construct an impossible session that fits no room
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00",), slot_ends=("10:00",))
    teacher = Teacher(teacher_id="T01", name="Dr. Rao")
    room = Room(room_id="R101", name="R101", room_type="lecture", capacity=20)
    div = Division(division_id="A", name="Div A", student_count=100, enrolled_courses=("C1",))
    course = Course(
        course_id="C1",
        name="C1",
        teacher_id="T01",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    sess = ClassSession(
        session_id="C1|A|1",
        course_id="C1",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=100,  # exceeds room capacity 20!
    )
    inst = SchedulingInstance(
        name="impossible_inst",
        grid=grid,
        teachers={"T01": teacher},
        rooms={"R101": room},
        divisions={"A": div},
        courses={"C1": course},
        sessions=(sess,),
        meta={},
    )
    problem = build_csp(inst)
    assert problem.root_wipeout == "C1|A|1"
    assert len(problem.domains["C1|A|1"]) == 0
