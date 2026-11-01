"""Unit and fuzz tests for DomainState reversible domain trail."""
from __future__ import annotations

import random
import pytest

from csp.problem import build_csp
from csp.trail import DomainState
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


@pytest.fixture
def sample_problem():
    grid = TimeGrid(
        day_names=("Mon", "Tue"),
        slot_starts=("09:00", "10:00", "11:00"),
        slot_ends=("10:00", "11:00", "12:00"),
    )
    teachers = {
        "T1": Teacher(teacher_id="T1", name="Teacher 1"),
        "T2": Teacher(teacher_id="T2", name="Teacher 2"),
    }
    rooms = {
        "R1": Room(room_id="R1", name="Room 1", room_type="lecture", capacity=50),
        "R2": Room(room_id="R2", name="Room 2", room_type="lecture", capacity=50),
    }
    divisions = {
        "A": Division(
            division_id="A",
            name="Div A",
            student_count=40,
            enrolled_courses=("C1", "C2"),
        )
    }
    courses = {
        "C1": Course(
            course_id="C1",
            name="Course 1",
            teacher_id="T1",
            sessions_per_week=1,
            duration_slots=1,
            room_types=("lecture",),
            eligible_divisions=("A",),
        ),
        "C2": Course(
            course_id="C2",
            name="Course 2",
            teacher_id="T2",
            sessions_per_week=1,
            duration_slots=1,
            room_types=("lecture",),
            eligible_divisions=("A",),
        ),
    }
    sessions = expand_sessions(courses, divisions)
    inst = SchedulingInstance(
        name="test_inst",
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    return build_csp(inst)


def test_basic_remove_checkpoint_restore(sample_problem):
    state = DomainState(sample_problem)
    v1 = sample_problem.variables[0]
    initial_size = state.size[v1]
    initial_snapshot = state.snapshot()

    mark0 = state.checkpoint()
    assert mark0 == 0

    # Prune first value
    state.remove(v1, 0)
    assert state.alive[v1][0] is False
    assert state.size[v1] == initial_size - 1
    assert 0 not in state.alive_indices(v1)

    # Prune second value
    state.remove(v1, 1)
    assert state.alive[v1][1] is False
    assert state.size[v1] == initial_size - 2
    assert 1 not in state.alive_indices(v1)

    # Restore to mark0
    state.restore(mark0)
    assert state.snapshot() == initial_snapshot
    assert state.size[v1] == initial_size
    assert 0 in state.alive_indices(v1)
    assert 1 in state.alive_indices(v1)


def test_nested_checkpoints(sample_problem):
    state = DomainState(sample_problem)
    v1 = sample_problem.variables[0]
    v2 = sample_problem.variables[1]

    mark0 = state.checkpoint()
    snap0 = state.snapshot()

    state.remove(v1, 0)
    mark1 = state.checkpoint()
    snap1 = state.snapshot()

    state.remove(v2, 0)
    state.remove(v2, 1)
    mark2 = state.checkpoint()
    snap2 = state.snapshot()

    state.remove(v1, 1)

    # Restore to mark2
    state.restore(mark2)
    assert state.snapshot() == snap2

    # Restore to mark1
    state.restore(mark1)
    assert state.snapshot() == snap1

    # Restore to mark0
    state.restore(mark0)
    assert state.snapshot() == snap0


def test_removed_since(sample_problem):
    state = DomainState(sample_problem)
    v1 = sample_problem.variables[0]
    v2 = sample_problem.variables[1]

    mark0 = state.checkpoint()
    state.remove(v1, 0)
    state.remove(v1, 1)
    assert state.removed_since(mark0) == {v1}

    mark1 = state.checkpoint()
    state.remove(v2, 0)
    assert state.removed_since(mark1) == {v2}
    assert state.removed_since(mark0) == {v1, v2}


def test_size_invariant(sample_problem):
    state = DomainState(sample_problem)
    for v in sample_problem.variables:
        assert state.size[v] == sum(state.alive[v])

    state.remove(sample_problem.variables[0], 0)
    for v in sample_problem.variables:
        assert state.size[v] == sum(state.alive[v])


def test_random_fuzz_restore(sample_problem):
    rng = random.Random(42)
    state = DomainState(sample_problem)
    variables = list(sample_problem.variables)

    # Stack of (checkpoint_mark, expected_snapshot)
    stack: list[tuple[int, dict[str, tuple[bool, ...]]]] = []

    for _ in range(500):
        action = rng.choice(["checkpoint", "remove", "restore"])

        if action == "checkpoint" or not stack:
            mark = state.checkpoint()
            snap = state.snapshot()
            stack.append((mark, snap))

        elif action == "remove":
            # Pick a random variable that has alive values
            candidates = [v for v in variables if state.size[v] > 0]
            if candidates:
                v = rng.choice(candidates)
                idx = rng.choice(state.alive_indices(v))
                state.remove(v, idx)
                # Verify size invariant
                assert state.size[v] == sum(state.alive[v])

        elif action == "restore" and stack:
            # Backtrack to the most recent checkpoint
            mark, expected_snap = stack.pop()
            state.restore(mark)
            assert state.snapshot() == expected_snap
            for v in variables:
                assert state.size[v] == sum(state.alive[v])

    # Unwind remaining stack to initial state
    while stack:
        mark, expected_snap = stack.pop()
        state.restore(mark)
        assert state.snapshot() == expected_snap
