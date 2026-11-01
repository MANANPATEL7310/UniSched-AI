"""Unit tests for soft constraints evaluation and reporting."""
from __future__ import annotations

import pytest

from data.loader import load_sample
from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance
from models.room import Room
from models.session import ClassSession
from models.teacher import Teacher
from models.timeslot import TimeGrid
from scheduling.soft_constraints import SoftReport, SoftWeights, soft_penalty


def make_simple_instance() -> SchedulingInstance:
    """Create a minimal 2-day x 4-slot instance with 4 sessions."""
    grid = TimeGrid(
        day_names=("Mon", "Tue"),
        slot_starts=("09:00", "10:00", "11:00", "12:00"),
        slot_ends=("10:00", "11:00", "12:00", "13:00"),
    )

    t1 = Teacher(
        teacher_id="T1",
        name="Teacher 1",
        preferred=frozenset({(0, 0), (0, 1), (0, 2), (0, 3)}),
        max_daily_sessions=None,
    )
    t2 = Teacher(
        teacher_id="T2",
        name="Teacher 2",
        preferred=frozenset(),
        max_daily_sessions=1,
    )

    d1 = Division(division_id="D1", name="Division 1", student_count=30, enrolled_courses=("C1",))
    d2 = Division(division_id="D2", name="Division 2", student_count=30, enrolled_courses=("C2",))

    r1 = Room(room_id="R1", name="Room 1", capacity=50, room_type="lecture")

    c1 = Course(
        course_id="C1",
        name="Course 1",
        teacher_id="T1",
        sessions_per_week=2,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("D1",),
    )
    c2 = Course(
        course_id="C2",
        name="Course 2",
        teacher_id="T2",
        sessions_per_week=2,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("D2",),
    )

    s1 = ClassSession(
        session_id="S1",
        course_id="C1",
        division_id="D1",
        teacher_id="T1",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )
    s2 = ClassSession(
        session_id="S2",
        course_id="C1",
        division_id="D1",
        teacher_id="T1",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )
    s3 = ClassSession(
        session_id="S3",
        course_id="C2",
        division_id="D2",
        teacher_id="T2",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )
    s4 = ClassSession(
        session_id="S4",
        course_id="C2",
        division_id="D2",
        teacher_id="T2",
        duration_slots=1,
        room_types=("lecture",),
        required_capacity=30,
    )

    return SchedulingInstance(
        name="4-session-test",
        grid=grid,
        teachers={"T1": t1, "T2": t2},
        rooms={"R1": r1},
        divisions={"D1": d1, "D2": d2},
        courses={"C1": c1, "C2": c2},
        sessions=(s1, s2, s3, s4),
        meta={},
    )


class TestSoftConstraints:
    def test_hand_computed_gaps_on_four_sessions(self):
        instance = make_simple_instance()

        # S1: Day 0, Slot 0
        # S2: Day 0, Slot 2 (gap of 1 empty slot at slot 1 for D1 and T1)
        # S3: Day 1, Slot 0
        # S4: Day 1, Slot 1 (consecutive, 0 gap for D2 and T2)
        assignment = {
            "S1": Assignment(day=0, start_slot=0, room_id="R1"),
            "S2": Assignment(day=0, start_slot=2, room_id="R1"),
            "S3": Assignment(day=1, start_slot=0, room_id="R1"),
            "S4": Assignment(day=1, start_slot=1, room_id="R1"),
        }

        report = soft_penalty(instance, assignment)

        # 1. Student gap: D1 has gap of 1 (slots 0 and 2 on Day 0), D2 has 0
        assert report.student_gap == 1.0
        assert report.details["by_division_gap"]["D1"] == 1.0
        assert report.details["by_division_gap"]["D2"] == 0.0

        # 2. Teacher gap: T1 has gap of 1 (slots 0 and 2 on Day 0), T2 has 0
        assert report.teacher_gap == 1.0
        assert report.details["by_teacher_gap"]["T1"] == 1.0
        assert report.details["by_teacher_gap"]["T2"] == 0.0

        # 3. Workload:
        # T1 (max_daily=None) has 2 sessions on Day 0, 0 on Day 1. Active days: [2]. Spread = 0.
        # T2 (max_daily=1) has 2 sessions on Day 1 -> overage = 2 - 1 = 1.
        assert report.workload == 1.0
        assert report.details["by_teacher_workload"]["T1"] == 0.0
        assert report.details["by_teacher_workload"]["T2"] == 1.0

        # 4. Preference:
        # T1 prefers (0, 0), (0, 1), (0, 2), (0, 3). S1 and S2 are at (0, 0) and (0, 2). All preferred -> 0.
        # T2 has empty preferred set -> 0.
        assert report.preference == 0.0

        # 5. Baseline:
        # None passed -> change = 0.0
        assert report.change == 0.0

        # Total weighted sum (all weights 1.0): 1 + 1 + 1 + 0 + 0 = 3.0
        assert report.total == 3.0

    def test_custom_weights(self):
        instance = make_simple_instance()
        assignment = {
            "S1": Assignment(day=0, start_slot=0, room_id="R1"),
            "S2": Assignment(day=0, start_slot=2, room_id="R1"),
            "S3": Assignment(day=1, start_slot=0, room_id="R1"),
            "S4": Assignment(day=1, start_slot=1, room_id="R1"),
        }

        custom_weights = SoftWeights(
            w_student_gap=2.5,
            w_teacher_gap=1.5,
            w_workload=4.0,
            w_preference=10.0,
            w_change=0.5,
        )

        report = soft_penalty(instance, assignment, weights=custom_weights)
        # Expected: 2.5*1 + 1.5*1 + 4.0*1 + 0 + 0 = 8.0
        assert report.total == 8.0

    def test_preference_violations(self):
        instance = make_simple_instance()
        # Move S1 to Day 1, Slot 3 (outside T1's preferred slots)
        assignment = {
            "S1": Assignment(day=1, start_slot=3, room_id="R1"),
            "S2": Assignment(day=0, start_slot=0, room_id="R1"),
            "S3": Assignment(day=1, start_slot=0, room_id="R1"),
            "S4": Assignment(day=1, start_slot=1, room_id="R1"),
        }

        report = soft_penalty(instance, assignment)
        assert report.preference == 1.0
        assert report.details["by_teacher_preference"]["T1"] == 1.0

    def test_baseline_change_penalty(self):
        instance = make_simple_instance()
        current_asgn = {
            "S1": Assignment(day=0, start_slot=0, room_id="R1"),
            "S2": Assignment(day=0, start_slot=1, room_id="R1"),
            "S3": Assignment(day=1, start_slot=0, room_id="R1"),
            "S4": Assignment(day=1, start_slot=1, room_id="R1"),
        }

        # Baseline had S2 at slot 2 and S4 at Day 0
        baseline = {
            "S1": (0, 0, "R1"),
            "S2": (0, 2, "R1"),  # Changed
            "S3": Assignment(day=1, start_slot=0, room_id="R1"),  # Unchanged
            "S4": (0, 1, "R1"),  # Changed
        }

        report = soft_penalty(instance, current_asgn, baseline=baseline)
        assert report.change == 2.0
        assert set(report.details["changed_sessions"]) == {"S2", "S4"}

    def test_multislot_sessions_no_false_gap(self):
        """A 2-slot session occupying slots 1 and 2 followed by slot 3 has 0 gap."""
        grid = TimeGrid(
            day_names=("Mon",),
            slot_starts=("09:00", "10:00", "11:00", "12:00"),
            slot_ends=("10:00", "11:00", "12:00", "13:00"),
        )
        t = Teacher(teacher_id="T1", name="T1")
        d = Division(division_id="D1", name="D1", student_count=20, enrolled_courses=("C1", "C2"))
        r = Room(room_id="R1", name="R1", capacity=30, room_type="lab")
        c1 = Course(course_id="C1", name="Lab", teacher_id="T1", sessions_per_week=1, duration_slots=2, room_types=("lab",), eligible_divisions=("D1",))
        c2 = Course(course_id="C2", name="Lec", teacher_id="T1", sessions_per_week=1, duration_slots=1, room_types=("lab",), eligible_divisions=("D1",))

        s_lab = ClassSession("S_LAB", "C1", "D1", "T1", 2, ("lab",), 20)
        s_lec = ClassSession("S_LEC", "C2", "D1", "T1", 1, ("lab",), 20)

        instance = SchedulingInstance(
            name="multislot",
            grid=grid,
            teachers={"T1": t},
            rooms={"R1": r},
            divisions={"D1": d},
            courses={"C1": c1, "C2": c2},
            sessions=(s_lab, s_lec),
            meta={},
        )

        # Lab at slot 1 (spans 1, 2); Lec at slot 3. Total slots = {1, 2, 3}. Gap = 0.
        asgn = {
            "S_LAB": Assignment(day=0, start_slot=1, room_id="R1"),
            "S_LEC": Assignment(day=0, start_slot=3, room_id="R1"),
        }
        report = soft_penalty(instance, asgn)
        assert report.student_gap == 0.0
        assert report.teacher_gap == 0.0

    def test_tiny_sample_soft_penalty(self):
        draft = load_sample("tiny")
        from data.loader import instance_from_draft
        from scheduling.scheduler import generate_timetable
        from csp.result import PRESETS

        instance = instance_from_draft(draft)
        cfg = PRESETS["A"]
        outcome = generate_timetable(instance, cfg)

        assert outcome.is_valid is True
        assert outcome.soft is not None
        assert isinstance(outcome.soft, SoftReport)
        assert outcome.soft.total >= 0.0
