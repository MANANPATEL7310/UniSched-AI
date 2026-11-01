"""Unit tests for CSP constraints: unary_ok and occupancy_keys."""
from __future__ import annotations

import pytest

from csp.constraints import occupancy_keys, unary_ok
from models import (
    Assignment,
    ClassSession,
    Course,
    Division,
    Room,
    SchedulingInstance,
    Teacher,
    TimeGrid,
)


@pytest.fixture
def sample_instance():
    grid = TimeGrid(
        day_names=("Mon", "Tue"),
        slot_starts=("09:00", "10:00", "11:00"),
        slot_ends=("10:00", "11:00", "12:00"),
    )
    teachers = {
        "T01": Teacher(
            teacher_id="T01",
            name="Dr. Rao",
            unavailable=frozenset([(0, 0), (1, 2)]),  # Mon@09:00, Tue@11:00
        ),
        "T02": Teacher(teacher_id="T02", name="Dr. Sharma"),
    }
    rooms = {
        "R101": Room(
            room_id="R101",
            name="Room 101",
            room_type="lecture",
            capacity=60,
            unavailable=frozenset([(0, 1)]),  # Mon@10:00
        ),
        "C101": Room(
            room_id="C101",
            name="Lab 101",
            room_type="computer_lab",
            capacity=40,
        ),
    }
    divisions = {
        "A": Division(
            division_id="A",
            name="Div A",
            student_count=50,
            enrolled_courses=("FAI",),
        )
    }
    courses = {
        "FAI": Course(
            course_id="FAI",
            name="AI",
            teacher_id="T01",
            sessions_per_week=1,
            duration_slots=1,
            room_types=("lecture",),
            eligible_divisions=("A",),
        )
    }
    return SchedulingInstance(
        name="test_inst",
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=(),
        meta={},
    )


def test_unary_ok_bounds_and_room(sample_instance):
    sess = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
    )

    # Valid placement: Mon slot 2 (11:00) in R101
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=2, room_id="R101")) is True

    # Day out of bounds (< 0 or >= 2)
    assert unary_ok(sample_instance, sess, Assignment(day=-1, start_slot=2, room_id="R101")) is False
    assert unary_ok(sample_instance, sess, Assignment(day=2, start_slot=2, room_id="R101")) is False

    # Slot out of bounds (< 0 or >= 3)
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=-1, room_id="R101")) is False
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=3, room_id="R101")) is False

    # Room does not exist
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=2, room_id="UNKNOWN")) is False


def test_unary_ok_duration_overflow(sample_instance):
    # Session with duration 2 slots on a 3-slot day (0, 1, 2)
    lab_sess = ClassSession(
        session_id="LAB|A|1",
        course_id="LAB",
        division_id="A",
        teacher_id="T02",
        duration_slots=2,
        room_types=("computer_lab",),
        required_capacity=40,
    )
    # Starts at slot 0 -> occupies 0, 1 (valid)
    assert unary_ok(sample_instance, lab_sess, Assignment(day=0, start_slot=0, room_id="C101")) is True
    # Starts at slot 1 -> occupies 1, 2 (valid)
    assert unary_ok(sample_instance, lab_sess, Assignment(day=0, start_slot=1, room_id="C101")) is True
    # Starts at slot 2 -> occupies 2, 3 (exceeds day length 3!)
    assert unary_ok(sample_instance, lab_sess, Assignment(day=0, start_slot=2, room_id="C101")) is False


def test_unary_ok_room_type(sample_instance):
    sess = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T02",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )
    # R101 is lecture -> allowed
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=0, room_id="R101")) is True
    # C101 is computer_lab -> rejected
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=0, room_id="C101")) is False


def test_unary_ok_capacity(sample_instance):
    # Required capacity = 50
    sess = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T02",
        duration_slots=1,
        room_types=("lecture", "computer_lab"),
        required_capacity=50,
    )
    # R101 capacity 60 >= 50 -> OK
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=0, room_id="R101")) is True
    # C101 capacity 40 < 50 -> rejected
    assert unary_ok(sample_instance, sess, Assignment(day=0, start_slot=0, room_id="C101")) is False

    # Exact boundary: required capacity 40 in room with capacity 40 -> OK
    sess_exact = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T02",
        duration_slots=1,
        room_types=("computer_lab",),
        required_capacity=40,
    )
    assert unary_ok(sample_instance, sess_exact, Assignment(day=0, start_slot=0, room_id="C101")) is True


def test_unary_ok_unavailability(sample_instance):
    # T01 is unavailable at Mon@09:00 (0, 0) and Tue@11:00 (1, 2)
    # R101 is unavailable at Mon@10:00 (0, 1)
    sess_t01 = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
    )

    # Teacher unavailable at (0, 0)
    assert unary_ok(sample_instance, sess_t01, Assignment(day=0, start_slot=0, room_id="R101")) is False
    # Room unavailable at (0, 1)
    assert unary_ok(sample_instance, sess_t01, Assignment(day=0, start_slot=1, room_id="R101")) is False
    # Both available at (0, 2) -> OK
    assert unary_ok(sample_instance, sess_t01, Assignment(day=0, start_slot=2, room_id="R101")) is True

    # Multi-slot session spanning an unavailable slot
    lab_sess = ClassSession(
        session_id="LAB|A|1",
        course_id="LAB",
        division_id="A",
        teacher_id="T01",
        duration_slots=2,
        room_types=("lecture",),
        required_capacity=50,
    )
    # Starts at Tue slot 1 (occupies slot 1 and 2). Slot 2 is unavailable for T01 -> rejected!
    assert unary_ok(sample_instance, lab_sess, Assignment(day=1, start_slot=1, room_id="R101")) is False
    # Starts at Tue slot 0 (occupies slot 0 and 1). Both free for T01 and R101 -> OK!
    assert unary_ok(sample_instance, lab_sess, Assignment(day=1, start_slot=0, room_id="R101")) is True


def test_unary_ok_fixed_assignment(sample_instance):
    fixed_val = Assignment(day=0, start_slot=2, room_id="R101")
    sess_fixed = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
        fixed=fixed_val,
    )
    # Matches fixed placement -> True
    assert unary_ok(sample_instance, sess_fixed, fixed_val) is True
    # Different placement -> False
    assert unary_ok(sample_instance, sess_fixed, Assignment(day=1, start_slot=0, room_id="R101")) is False


def test_occupancy_keys_structure():
    sess1 = ClassSession(
        session_id="FAI|A|1",
        course_id="FAI",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=50,
    )
    # Day 0, Slot 1, Room R101 with 3 slots per day: abs_slot = 0*3 + 1 = 1
    keys1 = occupancy_keys(sess1, Assignment(day=0, start_slot=1, room_id="R101"), slots_per_day=3)
    assert keys1 == frozenset([
        ("T", "T01", 1),
        ("D", "A", 1),
        ("R", "R101", 1),
    ])

    # 2-slot session: Day 1, Slot 0 -> abs slots: 1*3 + 0 = 3, and 3 + 1 = 4
    lab = ClassSession(
        session_id="LAB|B|1",
        course_id="LAB",
        division_id="B",
        teacher_id="T02",
        duration_slots=2,
        room_types=("computer_lab",),
        required_capacity=30,
    )
    keys_lab = occupancy_keys(lab, Assignment(day=1, start_slot=0, room_id="C101"), slots_per_day=3)
    assert len(keys_lab) == 6
    assert keys_lab == frozenset([
        ("T", "T02", 3),
        ("D", "B", 3),
        ("R", "C101", 3),
        ("T", "T02", 4),
        ("D", "B", 4),
        ("R", "C101", 4),
    ])


def test_occupancy_keys_touching_vs_overlapping():
    slots_per_day = 4

    # Session 1: 1 slot at Day 0, Slot 1 -> abs slot 1
    s1 = ClassSession(
        session_id="C1|A|1",
        course_id="C1",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )
    a1 = Assignment(day=0, start_slot=1, room_id="R101")
    k1 = occupancy_keys(s1, a1, slots_per_day)

    # Session 2: 2 slots at Day 0, Slot 2 -> abs slots 2 and 3 (Touching intervals [1, 2) and [2, 4))
    s2 = ClassSession(
        session_id="C2|A|1",
        course_id="C2",
        division_id="A",  # Same division!
        teacher_id="T01",  # Same teacher!
        duration_slots=2,
        room_types=("lecture",),
        required_capacity=30,
    )
    a2_touching = Assignment(day=0, start_slot=2, room_id="R101")  # Same room!
    k2_touching = occupancy_keys(s2, a2_touching, slots_per_day)

    # Touching intervals share NO keys: disjoint is True!
    assert k1.isdisjoint(k2_touching) is True

    # Overlapping interval: Session 2 placed at Day 0, Slot 1 -> abs slots 1 and 2
    a2_overlapping = Assignment(day=0, start_slot=1, room_id="R101")
    k2_overlapping = occupancy_keys(s2, a2_overlapping, slots_per_day)

    # Overlapping intervals share keys: disjoint is False!
    assert k1.isdisjoint(k2_overlapping) is False
    overlap = k1.intersection(k2_overlapping)
    assert ("T", "T01", 1) in overlap
    assert ("D", "A", 1) in overlap
    assert ("R", "R101", 1) in overlap


def test_occupancy_keys_cross_day_independence():
    # Same slot index and room on different days must never clash
    s = ClassSession(
        session_id="C|A|1",
        course_id="C",
        division_id="A",
        teacher_id="T01",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )
    k_mon = occupancy_keys(s, Assignment(day=0, start_slot=1, room_id="R101"), slots_per_day=6)
    k_tue = occupancy_keys(s, Assignment(day=1, start_slot=1, room_id="R101"), slots_per_day=6)

    assert k_mon.isdisjoint(k_tue) is True
