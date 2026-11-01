"""Unit tests for MRV, Degree, and LCV heuristics and Config B search."""
from __future__ import annotations

import pytest

from csp.backtracking import _Ctx, solve
from csp.heuristics import count_legal, lcv_score, order_values, select_variable
from csp.problem import build_csp
from csp.result import PRESETS, SearchConfig, SearchMetrics, SearchStatus
from csp.trail import DomainState
from data.loader import instance_from_draft, list_samples, load_sample
from models import (
    Assignment,
    Course,
    Division,
    Room,
    SchedulingInstance,
    Teacher,
    TimeGrid,
    expand_sessions,
)
from scheduling.timetable_validator import validate_timetable


@pytest.fixture
def worked_example_instance() -> SchedulingInstance:
    """1 day, 2 slots (0, 1), 2 rooms (R1, R2 cap 50).

    Teachers T1 (teaches X, Y), T2 (teaches Z).
    Division A (30 students).
    T2 unavailable at slot 0.
    Sessions: X|A|1 (T1), Y|A|1 (T1), Z|A|1 (T2).
    """
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00", "10:00"), slot_ends=("10:00", "11:00"))
    teachers = {
        "T1": Teacher(teacher_id="T1", name="Teacher 1"),
        "T2": Teacher(teacher_id="T2", name="Teacher 2", unavailable=frozenset([(0, 0)])),
    }
    rooms = {
        "R1": Room(room_id="R1", name="R1", room_type="lecture", capacity=50),
        "R2": Room(room_id="R2", name="R2", room_type="lecture", capacity=50),
    }
    divisions = {
        "A": Division(division_id="A", name="Div A", student_count=30, enrolled_courses=("X", "Y", "Z")),
    }
    courses = {
        "X": Course("X", "Course X", "T1", 1, 1, ("lecture",), ("A",)),
        "Y": Course("Y", "Course Y", "T1", 1, 1, ("lecture",), ("A",)),
        "Z": Course("Z", "Course Z", "T2", 1, 1, ("lecture",), ("A",)),
    }
    sessions = expand_sessions(courses, divisions)
    return SchedulingInstance("worked_example", grid, teachers, rooms, divisions, courses, sessions, meta={})


def test_mrv_picks_fewest_legal_values(worked_example_instance):
    problem = build_csp(worked_example_instance)
    # X has 4 values, Y has 4 values, Z has 2 values (slot 0 is unavailable for T2)
    assert len(problem.domains["X|A|1"]) == 4
    assert len(problem.domains["Y|A|1"]) == 4
    assert len(problem.domains["Z|A|1"]) == 2

    state = DomainState(problem)
    config = SearchConfig(name="B", use_mrv=True, use_degree=True, use_lcv=True)
    ctx = _Ctx(problem, config, None, state, SearchMetrics(), 0.0)

    # MRV must pick Z|A|1 first (2 values vs 4)
    chosen = select_variable(ctx)
    assert chosen == "Z|A|1"


def test_degree_tie_break():
    # Instance where variables have equal domain size (2), but strictly different degrees
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00", "10:00"), slot_ends=("10:00", "11:00"))
    teachers = {
        "T1": Teacher("T1", "T1"),
        "T2": Teacher("T2", "T2"),
        "T3": Teacher("T3", "T3"),
    }
    rooms = {
        "R1": Room("R1", "R1", "lecture", 50),
        "C1": Room("C1", "C1", "computer_lab", 50),
    }
    divisions = {
        "A": Division("A", "A", 30, ("C_HIGH", "C_NEIGHBOR1")),
        "B": Division("B", "B", 30, ("C_NEIGHBOR2",)),
        "C": Division("C", "C", 30, ("C_ISOLATED",)),
    }
    courses = {
        # C_HIGH needs lecture (R1). Shares Div A with C_NEIGHBOR1, shares Teacher T1 with C_NEIGHBOR2
        "C_HIGH": Course("C_HIGH", "High", "T1", 1, 1, ("lecture",), ("A",)),
        # C_NEIGHBOR1 needs computer_lab (C1). Shares Div A with C_HIGH
        "C_NEIGHBOR1": Course("C_NEIGHBOR1", "N1", "T2", 1, 1, ("computer_lab",), ("A",)),
        # C_NEIGHBOR2 needs computer_lab (C1). Shares Teacher T1 with C_HIGH
        "C_NEIGHBOR2": Course("C_NEIGHBOR2", "N2", "T1", 1, 1, ("computer_lab",), ("B",)),
        # C_ISOLATED needs lecture (R1), uses Teacher T3, Division C. Shares room R1 with C_HIGH only
        "C_ISOLATED": Course("C_ISOLATED", "Iso", "T3", 1, 1, ("lecture",), ("C",)),
    }
    sessions = expand_sessions(courses, divisions)
    inst = SchedulingInstance("deg_test", grid, teachers, rooms, divisions, courses, sessions, meta={})
    problem = build_csp(inst)

    # C_HIGH has neighbors: C_NEIGHBOR1 (via Div A), C_NEIGHBOR2 (via T1), C_ISOLATED (via R1) -> Degree 3
    # C_ISOLATED has neighbors: only C_HIGH (via R1) -> Degree 1
    assert len(problem.neighbors["C_HIGH|A|1"]) == 3
    assert len(problem.neighbors["C_ISOLATED|C|1"]) == 1

    state = DomainState(problem)
    config = SearchConfig(name="B", use_mrv=True, use_degree=True)
    ctx = _Ctx(problem, config, None, state, SearchMetrics(), 0.0)

    chosen = select_variable(ctx)
    assert chosen == "C_HIGH|A|1"


def test_lexicographical_id_tie_break():
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00", "10:00"), slot_ends=("10:00", "11:00"))
    teachers = {"T1": Teacher("T1", "T1")}
    rooms = {"R1": Room("R1", "R1", "lecture", 50)}
    divisions = {
        "A": Division("A", "A", 30, ("B_COURSE", "A_COURSE")),
    }
    courses = {
        "A_COURSE": Course("A_COURSE", "A", "T1", 1, 1, ("lecture",), ("A",)),
        "B_COURSE": Course("B_COURSE", "B", "T1", 1, 1, ("lecture",), ("A",)),
    }
    sessions = expand_sessions(courses, divisions)
    inst = SchedulingInstance("tie_test", grid, teachers, rooms, divisions, courses, sessions, meta={})
    problem = build_csp(inst)

    state = DomainState(problem)
    config = SearchConfig(name="B", use_mrv=True, use_degree=True)
    ctx = _Ctx(problem, config, None, state, SearchMetrics(), 0.0)

    # Both have domain size 2 and identical degree (neighbors: each other)
    chosen = select_variable(ctx)
    assert chosen == "A_COURSE|A|1"  # Lexicographically smaller session_id


def test_lcv_ordering(worked_example_instance):
    problem = build_csp(worked_example_instance)
    state = DomainState(problem)
    config = SearchConfig(name="B", use_mrv=True, use_degree=True, use_lcv=True)
    ctx = _Ctx(problem, config, None, state, SearchMetrics(), 0.0)

    # Values for Z|A|1 are (1, R1) and (1, R2).
    # Since division A is shared, both values rule out slot 1 for X and Y in the same room.
    ordered = order_values(ctx, "Z|A|1")
    assert len(ordered) == 2
    # Deterministic order preserved on tie
    assert ordered == [0, 1]


def test_config_b_solves_tiny_and_valid():
    inst = instance_from_draft(load_sample("tiny"))
    problem = build_csp(inst)

    res = solve(problem, PRESETS["B"])
    assert res.status == SearchStatus.SOLVED
    assert res.assignment is not None
    assert len(res.assignment) == 5

    report = validate_timetable(inst, res.assignment)
    assert report.is_valid is True
    assert len(report.violations) == 0


def test_config_b_all_named_instances_expected_statuses():
    samples = list_samples()
    for s in samples:
        inst = instance_from_draft(load_sample(s.name))
        problem = build_csp(inst)
        res = solve(problem, PRESETS["B"])

        # Expected status lookup
        import json
        from pathlib import Path
        exp_file = Path("data/sample_data") / s.name / "expected.json"
        if exp_file.exists():
            exp_data = json.loads(exp_file.read_text(encoding="utf-8"))
            expected_status = exp_data.get("expected_status")
            assert res.status.value == expected_status, f"{s.name} got {res.status.value}, expected {expected_status}"

        if res.status == SearchStatus.SOLVED:
            assert res.assignment is not None
            report = validate_timetable(inst, res.assignment)
            assert report.is_valid is True, f"{s.name} timetable is invalid under independent validator!"
