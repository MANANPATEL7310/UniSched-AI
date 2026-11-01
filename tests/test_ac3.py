"""Unit, integration, and soundness tests for AC-3 arc consistency."""
from __future__ import annotations

import random
import pytest

from csp.ac3 import ac3, ac3_root, revise, root_arcs
from csp.backtracking import _Ctx, solve
from csp.problem import build_csp
from csp.result import PRESETS, SearchConfig, SearchMetrics, SearchStatus
from csp.trail import DomainState
from data.generator import GeneratorConfig, generate_instance
from data.loader import instance_from_draft, load_sample
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.teacher import Teacher
from models.timeslot import TimeGrid
from tests.helpers.bruteforce import find_all_solutions


def _make_test_ctx(problem, config=None):
    cfg = config or PRESETS["D"]
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


def test_revise_prunes_unsupported_value():
    # Construct a 2-variable problem where X1 has 2 values, but value 0 has no support in X2
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00", "10:00"), slot_ends=("10:00", "11:00"))
    rooms = {"R1": Room(room_id="R1", name="R1", room_type="lecture", capacity=50)}
    teachers = {"T1": Teacher(teacher_id="T1", name="T1")}
    divisions = {
        "D1": Division(division_id="D1", name="D1", student_count=30, enrolled_courses=("C1",)),
        "D2": Division(division_id="D2", name="D2", student_count=30, enrolled_courses=("C2",)),
    }
    # C1 has teacher T1, C2 has teacher T1.
    # C2 has teacher unavailability on Mon 10:00, so C2 can only take Mon 09:00.
    teachers["T1"] = Teacher(teacher_id="T1", name="T1", unavailable=frozenset())
    # To restrict C2, make division D2 unavailable at 10:00 (or fixed assignment)
    courses = {
        "C1": Course("C1", "C1", "T1", sessions_per_week=1, duration_slots=1, room_types=("lecture",), eligible_divisions=("D1",)),
        "C2": Course("C2", "C2", "T1", sessions_per_week=1, duration_slots=1, room_types=("lecture",), eligible_divisions=("D2",)),
    }
    sessions = expand_sessions(courses, divisions)
    inst = SchedulingInstance(
        name="revise_test",
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    prob = build_csp(inst)
    ctx = _make_test_ctx(prob)

    x1 = sessions[0].session_id
    x2 = sessions[1].session_id

    # Suppose X2 only has slot 0 alive (e.g. manually remove slot 1 from X2)
    ctx.state.remove(x2, 1)  # Remove slot 1 from X2
    assert ctx.state.size[x2] == 1

    # Now in X1, slot 0 conflicts with the ONLY remaining value of X2 (teacher T1 at slot 0)
    # Revise(X1, X2) should prune slot 0 from X1!
    modified = revise(ctx, x1, x2, count_as="root")
    assert modified is True
    assert not ctx.state.alive[x1][0]  # Slot 0 pruned because no support in X2
    assert ctx.state.alive[x1][1]      # Slot 1 remains supported
    assert ctx.metrics.root_pruned == 1


def test_revise_no_op_when_already_supported():
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    prob = build_csp(inst)
    ctx = _make_test_ctx(prob)

    x1 = "MATH|A|1"
    x2 = "FAI|A|2"

    initial_size = ctx.state.size[x1]
    modified = revise(ctx, x1, x2, count_as="root")
    # In tiny, initial domains are already supported on this arc
    assert modified is False
    assert ctx.state.size[x1] == initial_size


def test_ac3_wipeout_on_contradiction():
    # 2 sessions for the same teacher with only 1 slot in the entire grid
    grid = TimeGrid(day_names=("Mon",), slot_starts=("09:00",), slot_ends=("10:00",))
    rooms = {"R1": Room(room_id="R1", name="R1", room_type="lecture", capacity=50)}
    teachers = {"T1": Teacher(teacher_id="T1", name="T1")}
    divisions = {"D1": Division(division_id="D1", name="D1", student_count=30, enrolled_courses=("C1",))}
    courses = {
        "C1": Course("C1", "C1", "T1", sessions_per_week=2, duration_slots=1, room_types=("lecture",), eligible_divisions=("D1",)),
    }
    sessions = expand_sessions(courses, divisions)
    inst = SchedulingInstance(
        name="ac3_wipeout_test",
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=sessions,
        meta={},
    )
    prob = build_csp(inst)
    ctx = _make_test_ctx(prob)

    ok = ac3_root(ctx)
    assert ok is False
    assert ctx.metrics.domain_wipeouts >= 1


def test_ac3_root_prunes_impossible_sample():
    draft = load_sample("impossible")
    inst = instance_from_draft(draft)
    prob = build_csp(inst)
    ctx = _make_test_ctx(prob)

    # In impossible sample, T01 has only 1 available slot, but 2 sessions
    ok = ac3_root(ctx)
    assert ok is False
    assert ctx.metrics.domain_wipeouts >= 1


def test_ac3_soundness_against_brute_force_oracle():
    """Verify AC-3 soundness across >= 200 random tiny instances.

    Mathematical Invariant: AC-3 must NEVER prune any value that is part of
    at least one valid solution.
    """
    total_tested = 0
    rng = random.Random(42)

    for seed in range(1000, 1300):
        # Generate varied tiny instances with 2 days x 2 slots, 2 rooms, 2-3 sessions
        cfg = GeneratorConfig(
            name=f"sound_{seed}",
            num_days=2,
            slots_per_day=2,
            num_divisions=2,
            num_teachers=2,
            num_courses=2,
            num_rooms=2,
            sessions_per_course=(1, 2),
            lab_fraction=0.0,
            availability_density=0.2,
            tightness=0.4,
            seed=seed,
        )

        try:
            inst = generate_instance(cfg)
        except Exception:
            continue

        prob = build_csp(inst)
        if prob.root_wipeout is not None:
            continue

        # 1. Enumerate all ground-truth solutions via oracle
        all_solutions = find_all_solutions(prob)

        # 2. Collect every (variable, domain_idx) that appears in any solution
        solution_values: set[tuple[str, int]] = set()
        for sol in all_solutions:
            for sid, asgn in sol.items():
                for idx, cand in enumerate(prob.domains[sid]):
                    if (cand.day, cand.start_slot, cand.room_id) == (asgn.day, asgn.start_slot, asgn.room_id):
                        solution_values.add((sid, idx))
                        break

        # 3. Run AC-3 root propagation
        ctx = _make_test_ctx(prob)
        ac3_ok = ac3_root(ctx)

        if len(all_solutions) > 0:
            assert ac3_ok is True, f"AC-3 reported wipeout on solvable instance (seed {seed})"
            # SOUNDNESS CHECK: Every solution value MUST still be alive!
            for sid, val_idx in solution_values:
                assert ctx.state.alive[sid][val_idx], (
                    f"Soundness violation! AC-3 pruned valid solution value "
                    f"session={sid}, val_idx={val_idx} on seed {seed}"
                )
        else:
            # If no solutions exist, AC-3 may either wipe out (proving unsat) or leave some values
            pass

        total_tested += 1
        if total_tested >= 200:
            break

    assert total_tested >= 200, f"Expected at least 200 tested instances, got {total_tested}"
