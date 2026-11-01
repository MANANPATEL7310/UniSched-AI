"""Fuzz cross-check test suite across all CSP solvers (Stage 5, A19).

Verifies that Algorithms A, B, C, and D:
1. Agree completely on SOLVED vs INFEASIBLE_PROVEN across >= 300 random tiny instances,
   verified against the brute-force oracle.
2. Never report INFEASIBLE_PROVEN on >= 100 small planted instances with known solutions.
3. Every SOLVED timetable passes the independent validate_timetable with 0 violations.
"""
from __future__ import annotations

from dataclasses import replace
import random
import pytest

from csp.backtracking import solve
from csp.problem import build_csp
from csp.result import PRESETS as SOLVER_PRESETS, SearchStatus
from data.generator import PRESETS as GEN_PRESETS, generate_instance
from errors import GenerationError
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.teacher import Teacher
from models.timeslot import TimeGrid
from scheduling.timetable_validator import validate_timetable
from tests.helpers.bruteforce import is_satisfiable


def test_fuzz_crosscheck_300_tiny_instances():
    """Cross-check A, B, C, D on >= 300 random tiny instances against brute-force oracle."""
    total_tested = 300
    solved_count = 0
    infeasible_count = 0

    for s in range(total_tested):
        rng = random.Random(s + 20000)
        grid = TimeGrid(
            day_names=("Mon", "Tue"),
            slot_starts=("09:00", "10:00"),
            slot_ends=("10:00", "11:00"),
        )
        rooms = {
            "R1": Room(room_id="R1", name="Room 1", room_type="lecture", capacity=50),
            "R2": Room(room_id="R2", name="Room 2", room_type="lecture", capacity=60),
        }

        all_slots = [(0, 0), (0, 1), (1, 0), (1, 1)]
        unav1 = frozenset(rng.sample(all_slots, rng.randint(0, 3)))
        unav2 = frozenset(rng.sample(all_slots, rng.randint(0, 3)))

        teachers = {
            "T1": Teacher(teacher_id="T1", name="Teacher 1", unavailable=unav1),
            "T2": Teacher(teacher_id="T2", name="Teacher 2", unavailable=unav2),
        }
        divisions = {
            "D1": Division(division_id="D1", name="Division 1", student_count=30, enrolled_courses=("C1",)),
            "D2": Division(division_id="D2", name="Division 2", student_count=40, enrolled_courses=("C2",)),
        }
        courses = {
            "C1": Course(
                course_id="C1",
                name="Course 1",
                teacher_id="T1",
                sessions_per_week=rng.randint(1, 3),
                duration_slots=1,
                room_types=("lecture",),
                eligible_divisions=("D1",),
            ),
            "C2": Course(
                course_id="C2",
                name="Course 2",
                teacher_id="T2",
                sessions_per_week=rng.randint(1, 3),
                duration_slots=1,
                room_types=("lecture",),
                eligible_divisions=("D2",),
            ),
        }

        sessions = expand_sessions(courses, divisions)
        inst = SchedulingInstance(
            name=f"tiny_fuzz_{s}",
            grid=grid,
            teachers=teachers,
            rooms=rooms,
            divisions=divisions,
            courses=courses,
            sessions=tuple(sessions),
            meta={},
        )
        prob = build_csp(inst)

        # Oracle ground-truth satisfiability
        sat = is_satisfiable(prob)

        statuses: dict[str, SearchStatus] = {}
        for algo in ["A", "B", "C", "D"]:
            cfg = replace(SOLVER_PRESETS[algo], timeout_s=1.0)
            res = solve(prob, cfg)
            statuses[algo] = res.status

            if res.status == SearchStatus.SOLVED:
                assert sat is True, f"Oracle reported UNSAT, but Algo {algo} found solution on tiny {s}"
                report = validate_timetable(inst, res.assignment)
                assert report.is_valid is True, f"Validator failed on tiny {s} for Algo {algo}"
                assert len(report.violations) == 0
            elif res.status == SearchStatus.INFEASIBLE_PROVEN:
                assert sat is False, f"Oracle found solution, but Algo {algo} reported INFEASIBLE on tiny {s}"

        non_timeout = {st for st in statuses.values() if st != SearchStatus.TIMEOUT}
        assert len(non_timeout) <= 1, f"Disagreement between algorithms on tiny {s}: {statuses}"

        if SearchStatus.SOLVED in non_timeout:
            solved_count += 1
        elif SearchStatus.INFEASIBLE_PROVEN in non_timeout:
            infeasible_count += 1

    assert solved_count > 50, f"Expected varied instances with solutions, got {solved_count}"
    assert infeasible_count > 50, f"Expected varied instances without solutions, got {infeasible_count}"


def test_fuzz_crosscheck_100_small_planted_instances():
    """Cross-check A, B, C, D on >= 100 small planted instances with guaranteed solutions."""
    planted_count = 0
    solved_count = 0
    seed = 0

    while planted_count < 100:
        try:
            inst = generate_instance(replace(GEN_PRESETS["small"], seed=seed))
        except GenerationError:
            seed += 1
            continue
        seed += 1
        prob = build_csp(inst)

        statuses: dict[str, SearchStatus] = {}
        for algo in ["A", "B", "C", "D"]:
            # Algorithm A without heuristics gets 50ms; B, C, D get 0.5s
            t_limit = 0.05 if algo == "A" else 0.5
            cfg = replace(SOLVER_PRESETS[algo], timeout_s=t_limit)
            res = solve(prob, cfg)
            statuses[algo] = res.status

            # Planted instances must NEVER be proven infeasible
            assert res.status != SearchStatus.INFEASIBLE_PROVEN, (
                f"Planted small seed {seed-1} was reported INFEASIBLE by Algo {algo}"
            )

            # Every solved timetable must pass the independent validator
            if res.status == SearchStatus.SOLVED:
                report = validate_timetable(inst, res.assignment)
                assert report.is_valid is True, (
                    f"Validation failed for Algo {algo} on seed {seed-1}: {report.violations}"
                )
                assert len(report.violations) == 0

        # Completed (non-TIMEOUT) algorithms must all agree on SOLVED
        non_timeout = {st for st in statuses.values() if st != SearchStatus.TIMEOUT}
        assert len(non_timeout) <= 1, f"Disagreement on seed {seed-1}: {statuses}"

        if SearchStatus.SOLVED in non_timeout:
            solved_count += 1
        planted_count += 1

    assert planted_count == 100
    assert solved_count >= 90, f"Expected >= 90 solved small planted instances, got {solved_count}"

