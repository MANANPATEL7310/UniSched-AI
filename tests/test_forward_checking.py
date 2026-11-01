"""Unit and integration tests for Forward Checking (Config C)."""
from __future__ import annotations

import pytest

from csp.backtracking import _Ctx, solve
from csp.forward_checking import forward_check
from csp.problem import build_csp
from csp.result import PRESETS, SearchMetrics, SearchStatus
from csp.trail import DomainState
from data.loader import instance_from_draft, list_samples, load_sample
from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.teacher import Teacher
from models.timeslot import TimeGrid
from scheduling.timetable_validator import validate_timetable


def _make_test_ctx(problem, config=None):
    cfg = config or PRESETS["C"]
    state = DomainState(problem)
    metrics = SearchMetrics()
    return _Ctx(
        problem=problem,
        config=cfg,
        control=None,
        state=state,
        metrics=metrics,
        t0=0.0,
    )


def test_forward_check_prunes_conflicting_values():
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)
    ctx = _make_test_ctx(problem)

    sid = "MATH|A|1"
    val_idx = 0
    assigned_cand = problem.domains[sid][val_idx]

    # Pre-condition: check alive counts
    neighbor_sid = "MATH|B|1"  # Shares teacher T02 and room R101 at Mon 09:00 (slot 0)
    initial_alive = ctx.state.size[neighbor_sid]

    ctx.assignment[sid] = val_idx
    ctx.used |= problem.keys[sid][val_idx]

    ok = forward_check(ctx, sid, val_idx)
    assert ok is True
    assert ctx.metrics.values_pruned > 0
    assert ctx.state.size[neighbor_sid] < initial_alive

    # The specific slot conflicting with assigned_cand must be pruned in neighbor
    for i2, cand in enumerate(problem.domains[neighbor_sid]):
        if cand.day == assigned_cand.day and cand.start_slot == assigned_cand.start_slot:
            assert not ctx.state.alive[neighbor_sid][i2]


def test_forward_check_restore_exact():
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)
    ctx = _make_test_ctx(problem)

    initial_snapshot = ctx.state.snapshot()
    mark = ctx.state.checkpoint()

    sid = "MATH|A|1"
    val_idx = 0
    ctx.assignment[sid] = val_idx
    ctx.used |= problem.keys[sid][val_idx]

    ok = forward_check(ctx, sid, val_idx)
    assert ok is True
    assert ctx.metrics.values_pruned > 0

    # Restore to mark
    ctx.state.restore(mark)
    assert ctx.state.snapshot() == initial_snapshot
    for s in problem.variables:
        assert ctx.state.size[s] == len(problem.domains[s])


def test_forward_check_wipeout_returns_false():
    # Construct a minimal 2-variable problem where variable B has only 1 slot that conflicts with A
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00",), slot_ends=("10:00",))
    rooms = {"R1": Room(room_id="R1", name="R1", room_type="lecture", capacity=50)}
    teachers = {"T1": Teacher(teacher_id="T1", name="T1")}
    divisions = {"D1": Division(division_id="D1", name="D1", student_count=30, enrolled_courses=("C1", "C2"))}
    courses = {
        "C1": Course("C1", "C1", "T1", sessions_per_week=1, duration_slots=1, room_types=("lecture",), eligible_divisions=("D1",)),
        "C2": Course("C2", "C2", "T1", sessions_per_week=1, duration_slots=1, room_types=("lecture",), eligible_divisions=("D1",)),
    }
    sessions = expand_sessions(courses, divisions)
    instance = SchedulingInstance(
        name="wipeout_test",
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    problem = build_csp(instance)
    ctx = _make_test_ctx(problem)

    sid1 = sessions[0].session_id
    sid2 = sessions[1].session_id
    assert len(problem.domains[sid2]) == 1

    ctx.assignment[sid1] = 0
    ctx.used |= problem.keys[sid1][0]

    # Forward checking should prune the only value of sid2 and return False (wipeout)
    ok = forward_check(ctx, sid1, 0)
    assert ok is False
    assert ctx.metrics.domain_wipeouts == 1
    assert ctx.state.size[sid2] == 0


def test_forward_check_non_neighbour_untouched():
    # In tiny, PLAB|A|1 uses computer_lab C101, MATH|B|1 uses lecture R102, teacher T02 vs T01, div B vs A
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)
    ctx = _make_test_ctx(problem)

    sid = "PLAB|A|1"
    non_neighbour = "MATH|B|1"

    initial_size = ctx.state.size[non_neighbour]
    initial_alive = list(ctx.state.alive[non_neighbour])

    ctx.assignment[sid] = 0
    ctx.used |= problem.keys[sid][0]

    forward_check(ctx, sid, 0)

    # If non_neighbour shares no keys, alive values must be identical
    if not (problem.keys[sid][0] & set().union(*problem.keys[non_neighbour])):
        assert ctx.state.size[non_neighbour] == initial_size
        assert ctx.state.alive[non_neighbour] == initial_alive


def test_config_c_solves_tiny_and_valid():
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)

    res = solve(problem, PRESETS["C"])
    assert res.status == SearchStatus.SOLVED
    assert res.assignment is not None
    assert res.metrics.values_pruned > 0

    report = validate_timetable(instance, res.assignment)
    assert report.is_valid is True
    assert len(report.violations) == 0


@pytest.mark.parametrize("sample_name", [
    "feasible_obvious",
    "impossible",
    "multi_solution",
    "multihour_lab",
    "tight",
    "tiny",
    "unavailability",
])
def test_config_c_all_named_instances_expected_statuses(sample_name: str):
    draft = load_sample(sample_name)
    instance = instance_from_draft(draft)
    problem = build_csp(instance)

    expected_file = draft.get("expected")
    res = solve(problem, PRESETS["C"])

    if sample_name == "impossible":
        assert res.status == SearchStatus.INFEASIBLE_PROVEN
        assert res.assignment is None
    else:
        assert res.status == SearchStatus.SOLVED
        assert res.assignment is not None
        report = validate_timetable(instance, res.assignment)
        assert report.is_valid is True
