"""Unit tests for the scheduler facade and RunHandle thread worker."""
from __future__ import annotations

import time
import pytest

from csp.result import PRESETS, SearchConfig, SearchStatus
from data.loader import instance_from_draft, load_sample
from errors import InputValidationError
from models import (
    Course,
    Division,
    Room,
    SchedulingInstance,
    Teacher,
    TimeGrid,
    expand_sessions,
)
from scheduling.scheduler import generate_timetable, start_run


def test_generate_timetable_tiny_valid():
    inst = instance_from_draft(load_sample("tiny"))
    outcome = generate_timetable(inst, PRESETS["A"])

    assert outcome.status == SearchStatus.SOLVED
    assert outcome.is_valid is True
    assert outcome.timetable is not None
    assert outcome.validation is not None
    assert len(outcome.validation.violations) == 0
    assert outcome.num_sessions == 5
    assert outcome.build_s >= 0.0
    assert outcome.runtime_s >= 0.0
    assert "Valid assignment found" in outcome.message


def test_generate_timetable_input_validation_error():
    # Instance with an invalid course pointing to an unknown teacher
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00",), slot_ends=("10:00",))
    room = Room(room_id="R1", name="R1", room_type="lecture", capacity=50)
    div = Division(division_id="A", name="Div A", student_count=30, enrolled_courses=("C1",))
    course = Course(
        course_id="C1",
        name="C1",
        teacher_id="UNKNOWN_TEACHER",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    inst = SchedulingInstance(
        name="bad_inst",
        grid=grid,
        teachers={},
        rooms={"R1": room},
        divisions={"A": div},
        courses={"C1": course},
        sessions=expand_sessions({"C1": course}, {"A": div}),
        meta={},
    )

    with pytest.raises(InputValidationError) as exc_info:
        generate_timetable(inst, PRESETS["A"])

    assert any(issue.code == "UNKNOWN_TEACHER" for issue in exc_info.value.issues)


def test_start_run_async_completes():
    inst = instance_from_draft(load_sample("tiny"))
    handle = start_run(inst, PRESETS["A"])

    finished = handle.wait(timeout=5.0)
    assert finished is True
    assert handle.is_done() is True
    assert handle.error() is None

    outcome = handle.outcome()
    assert outcome is not None
    assert outcome.status == SearchStatus.SOLVED
    assert outcome.is_valid is True
    assert outcome.timetable is not None


def test_start_run_cancellation():
    inst = instance_from_draft(load_sample("tiny"))
    # Use a small timeout or immediate cancellation
    handle = start_run(inst, SearchConfig(name="A", timeout_s=10.0))
    handle.cancel()

    finished = handle.wait(timeout=5.0)
    assert finished is True
    assert handle.is_done() is True

    outcome = handle.outcome()
    assert outcome is not None
    assert outcome.status in (SearchStatus.CANCELLED, SearchStatus.SOLVED)


def test_runhandle_captures_exceptions():
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00",), slot_ends=("10:00",))
    room = Room(room_id="R1", name="R1", room_type="lecture", capacity=50)
    div = Division(division_id="A", name="Div A", student_count=30, enrolled_courses=("C1",))
    course = Course(
        course_id="C1",
        name="C1",
        teacher_id="MISSING_T",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    inst = SchedulingInstance(
        name="error_inst",
        grid=grid,
        teachers={},
        rooms={"R1": room},
        divisions={"A": div},
        courses={"C1": course},
        sessions=expand_sessions({"C1": course}, {"A": div}),
        meta={},
    )

    handle = start_run(inst, PRESETS["A"])
    finished = handle.wait(timeout=5.0)
    assert finished is True
    assert handle.is_done() is True
    assert handle.outcome() is None
    assert isinstance(handle.error(), InputValidationError)
