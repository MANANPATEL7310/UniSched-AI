"""Test that heuristic-based search (Config B) only alters variable/value ordering.

Verifies that any solution returned by Config B on small instances is a member of the
ground-truth solution set enumerated by the brute-force oracle.
"""
from __future__ import annotations

import pytest

from csp.backtracking import solve
from csp.problem import build_csp
from csp.result import PRESETS, SearchStatus
from data.loader import instance_from_draft, load_sample
from scheduling.timetable_validator import validate_timetable
from tests.helpers.bruteforce import find_all_solutions


@pytest.fixture
def tiny_problem():
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)
    return instance, problem


def test_tiny_oracle_and_config_b_membership(tiny_problem):
    instance, problem = tiny_problem

    # Enumerate all possible valid solutions using brute-force oracle
    all_solutions = find_all_solutions(problem)
    assert len(all_solutions) > 0, "Oracle should find at least one valid solution for tiny"

    # Solve with baseline Config A
    res_a = solve(problem, PRESETS["A"])
    assert res_a.status == SearchStatus.SOLVED
    assert res_a.assignment is not None
    assert res_a.assignment in all_solutions

    # Solve with heuristic-guided Config B (MRV + Degree + LCV)
    res_b = solve(problem, PRESETS["B"])
    assert res_b.status == SearchStatus.SOLVED
    assert res_b.assignment is not None
    assert res_b.assignment in all_solutions

    # Verify Config B solution passes the independent timetable validator
    report = validate_timetable(instance, res_b.assignment)
    assert report.is_valid is True
    assert len(report.violations) == 0


@pytest.mark.parametrize("sample_name", ["feasible_obvious", "multi_solution", "tight", "unavailability"])
def test_config_b_solution_in_oracle_solutions(sample_name: str):
    draft = load_sample(sample_name)
    instance = instance_from_draft(draft)
    problem = build_csp(instance)

    if len(problem.variables) <= 8:
        all_solutions = find_all_solutions(problem)
        assert len(all_solutions) > 0

        res_b = solve(problem, PRESETS["B"])
        assert res_b.status == SearchStatus.SOLVED
        assert res_b.assignment is not None
        assert res_b.assignment in all_solutions
    else:
        res_b = solve(problem, PRESETS["B"])
        assert res_b.status == SearchStatus.SOLVED


def test_impossible_instance_oracle_and_config_b():
    draft = load_sample("impossible")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)

    # Oracle confirms 0 solutions exist
    all_solutions = find_all_solutions(problem)
    assert len(all_solutions) == 0

    # Config B confirms INFEASIBLE_PROVEN
    res_b = solve(problem, PRESETS["B"])
    assert res_b.status == SearchStatus.INFEASIBLE_PROVEN
    assert res_b.assignment is None
