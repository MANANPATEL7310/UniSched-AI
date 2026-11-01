"""Unit tests for models and base exceptions."""
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from errors import DataLoadError, InputValidationError, TimetableError
from models import (
    ROOM_TYPES,
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


def test_timegrid_properties_and_methods():
    grid = TimeGrid(
        day_names=("Mon", "Tue"),
        slot_starts=("09:00", "10:00", "11:00"),
        slot_ends=("10:00", "11:00", "12:00"),
    )
    assert grid.num_days == 2
    assert grid.slots_per_day == 3
    assert grid.abs_slot(0, 0) == 0
    assert grid.abs_slot(1, 2) == 5

    assert grid.label(0, 1) == "Mon 10:00"
    with pytest.raises(ValueError, match="Day index"):
        grid.label(2, 0)
    with pytest.raises(ValueError, match="Slot index"):
        grid.label(0, 3)

    assert grid.parse("Mon@09:00") == (0, 0)
    assert grid.parse("Tue@11:00") == (1, 2)

    with pytest.raises(ValueError, match="expected 'DayName@HH:MM'"):
        grid.parse("Mon 09:00")
    with pytest.raises(ValueError, match="Unknown day 'Wed'"):
        grid.parse("Wed@09:00")
    with pytest.raises(ValueError, match="Unknown slot start '12:00'"):
        grid.parse("Mon@12:00")


def test_models_are_frozen():
    assignment = Assignment(day=0, start_slot=1, room_id="R101")
    with pytest.raises(FrozenInstanceError):
        assignment.day = 1  # type: ignore

    teacher = Teacher(teacher_id="T01", name="Dr. Rao")
    with pytest.raises(FrozenInstanceError):
        teacher.name = "Dr. Other"  # type: ignore


def test_expand_sessions():
    courses = {
        "FAI": Course(
            course_id="FAI",
            name="AI",
            teacher_id="T01",
            sessions_per_week=2,
            duration_slots=1,
            room_types=("lecture",),
            eligible_divisions=("A",),
        ),
        "MATH": Course(
            course_id="MATH",
            name="Math",
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
            duration_slots=2,
            room_types=("computer_lab",),
            eligible_divisions=("A",),
        ),
    }

    divisions = {
        "A": Division(
            division_id="A",
            name="Div A",
            student_count=50,
            enrolled_courses=("FAI", "MATH", "PLAB"),
        ),
        "B": Division(
            division_id="B",
            name="Div B",
            student_count=30,
            enrolled_courses=("MATH",),
        ),
    }

    fixed = {
        "FAI|A|1": Assignment(day=0, start_slot=1, room_id="R101"),
    }

    sessions = expand_sessions(courses, divisions, fixed)
    # Expected:
    # FAI: A (2) -> FAI|A|1, FAI|A|2
    # MATH: A (1) -> MATH|A|1; B (1) -> MATH|B|1
    # PLAB: A (1) -> PLAB|A|1
    # Total = 5
    assert len(sessions) == 5
    sids = [s.session_id for s in sessions]
    assert sids == sorted(sids)
    assert sids == ["FAI|A|1", "FAI|A|2", "MATH|A|1", "MATH|B|1", "PLAB|A|1"]

    # Verify fixed session assignment attached
    fixed_sess = next(s for s in sessions if s.session_id == "FAI|A|1")
    assert fixed_sess.fixed == Assignment(day=0, start_slot=1, room_id="R101")
    non_fixed = next(s for s in sessions if s.session_id == "FAI|A|2")
    assert non_fixed.fixed is None

    # Check capacity inherited from division
    assert fixed_sess.required_capacity == 50
    math_b = next(s for s in sessions if s.session_id == "MATH|B|1")
    assert math_b.required_capacity == 30


def test_errors_hierarchy():
    assert issubclass(DataLoadError, TimetableError)
    assert issubclass(InputValidationError, TimetableError)
    err = InputValidationError(["issue1", "issue2"])
    assert "2 issue(s)" in str(err)


def test_csp_result_types():
    from csp import (
        PRESETS,
        ProgressState,
        RunControl,
        SearchConfig,
        SearchMetrics,
        SearchResult,
        SearchStatus,
    )
    import threading

    assert SearchStatus.SOLVED.value == "SOLVED"
    assert SearchStatus.INFEASIBLE_PROVEN.value == "INFEASIBLE_PROVEN"
    assert SearchStatus.TIMEOUT.value == "TIMEOUT"
    assert SearchStatus.NODE_LIMIT.value == "NODE_LIMIT"
    assert SearchStatus.CANCELLED.value == "CANCELLED"

    assert "A" in PRESETS and "B" in PRESETS and "C" in PRESETS and "D" in PRESETS
    assert PRESETS["A"].use_mrv is False
    assert PRESETS["B"].use_mrv is True
    assert PRESETS["C"].use_forward_checking is True
    assert PRESETS["D"].use_ac3_root is True
    assert PRESETS["D"].use_mac is True

    metrics = SearchMetrics()
    assert metrics.nodes == 0
    assert metrics.attempts == 0
    assert metrics.backtracks == 0

    progress = ProgressState()
    assert progress.total == 0

    control = RunControl(cancel_event=threading.Event(), progress=progress)
    assert control.cancel_event.is_set() is False

    res = SearchResult(
        status=SearchStatus.SOLVED,
        assignment={},
        metrics=metrics,
        config=PRESETS["A"],
        message="OK",
    )
    assert res.status == SearchStatus.SOLVED


def test_tiny_fixture_solution_format():
    import json
    from pathlib import Path

    fixture_path = Path("tests/fixtures/tiny_solution.json")
    assert fixture_path.exists()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert data["instance_name"] == "tiny"
    assignments = data["assignments"]
    assert len(assignments) == 5
    for sid, val in assignments.items():
        assert len(val) == 3
        day, slot, room = val
        assert isinstance(day, int)
        assert isinstance(slot, int)
        assert isinstance(room, str)

