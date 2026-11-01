"""Unit tests for the baseline backtracking search engine."""
from __future__ import annotations

import threading
import pytest

from csp.backtracking import solve
from csp.problem import build_csp
from csp.result import PRESETS, ProgressState, RunControl, SearchConfig, SearchStatus
from data.loader import instance_from_draft, load_sample
from models import (
    Course,
    Division,
    Room,
    SchedulingInstance,
    Teacher,
    TimeGrid,
    expand_sessions,
)
from scheduling.timetable_validator import validate_timetable


def test_solve_tiny_solved():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    res = solve(problem, PRESETS["A"])
    assert res.status == SearchStatus.SOLVED
    assert res.assignment is not None
    assert len(res.assignment) == 5

    # Verify through independent validator
    report = validate_timetable(inst, res.assignment)
    assert report.is_valid is True
    assert len(report.violations) == 0
    assert report.sessions_assigned == 5

    # Check metrics collected
    assert res.metrics.nodes > 0
    assert res.metrics.attempts > 0
    assert res.metrics.checks > 0
    assert res.metrics.runtime_s >= 0.0


def test_solve_impossible_infeasible_proven():
    # Grid: 1 day, 1 slot. Teacher T01 teaches Course X for Division A with 2 sessions/week.
    # Pigeonhole principle: 2 sessions cannot be placed in 1 slot.
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00",), slot_ends=("10:00",))
    teacher = Teacher(teacher_id="T01", name="Dr. Rao")
    room = Room(room_id="R101", name="R101", room_type="lecture", capacity=50)
    div = Division(division_id="A", name="Div A", student_count=30, enrolled_courses=("X",))
    course = Course(
        course_id="X",
        name="Course X",
        teacher_id="T01",
        sessions_per_week=2,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("A",),
    )
    inst = SchedulingInstance(
        name="impossible",
        grid=grid,
        teachers={"T01": teacher},
        rooms={"R101": room},
        divisions={"A": div},
        courses={"X": course},
        sessions=expand_sessions({"X": course}, {"A": div}),
        meta={},
    )
    problem = build_csp(inst)
    assert problem.root_wipeout is None  # Each individual session has 1 valid placement

    res = solve(problem, PRESETS["A"])
    assert res.status == SearchStatus.INFEASIBLE_PROVEN
    assert res.assignment is None
    assert "no assignment satisfies all hard constraints" in res.message


def test_timeout_never_reports_infeasible():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    # Impose an impossibly tight 0-second timeout
    config = SearchConfig(name="A", timeout_s=0.000001)
    res = solve(problem, config)

    # Must be TIMEOUT, NEVER INFEASIBLE_PROVEN
    assert res.status == SearchStatus.TIMEOUT
    assert res.assignment is None
    assert "Time limit" in res.message


def test_node_limit_never_reports_infeasible():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    config = SearchConfig(name="A", node_limit=2)
    res = solve(problem, config)

    assert res.status == SearchStatus.NODE_LIMIT
    assert res.assignment is None
    assert "Node limit" in res.message


def test_cancellation():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    cancel_ev = threading.Event()
    cancel_ev.set()  # Cancel already requested before start
    control = RunControl(cancel_event=cancel_ev, progress=ProgressState())

    res = solve(problem, PRESETS["A"], control=control)
    assert res.status == SearchStatus.CANCELLED
    assert res.assignment is None
    assert "cancelled" in res.message


def test_determinism():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    res1 = solve(problem, PRESETS["A"])
    res2 = solve(problem, PRESETS["A"])

    assert res1.status == res2.status == SearchStatus.SOLVED
    assert res1.assignment == res2.assignment
    assert res1.metrics.nodes == res2.metrics.nodes
    assert res1.metrics.attempts == res2.metrics.attempts
    assert res1.metrics.backtracks == res2.metrics.backtracks
    assert res1.metrics.checks == res2.metrics.checks


def test_problem_domains_unchanged_after_solve():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    domains_before = {k: list(v) for k, v in problem.domains.items()}
    solve(problem, PRESETS["A"])
    domains_after = {k: list(v) for k, v in problem.domains.items()}

    assert domains_before == domains_after
