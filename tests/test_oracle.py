"""Unit tests for brute-force oracle (tests/helpers/bruteforce.py)."""
from __future__ import annotations

import pytest

from csp.problem import build_csp
from data.loader import instance_from_draft, load_sample
from scheduling.timetable_validator import validate_timetable
from tests.helpers.bruteforce import count_solutions, find_all_solutions, is_satisfiable


class TestBruteForceOracle:
    def test_oracle_on_tiny_finds_solutions(self):
        draft = load_sample("tiny")
        instance = instance_from_draft(draft)
        problem = build_csp(instance)

        solutions = find_all_solutions(problem)
        assert len(solutions) > 0, "Tiny instance should have at least 1 solution"
        assert is_satisfiable(problem) is True
        assert count_solutions(problem) == len(solutions)

        # Verify that EVERY solution found by oracle satisfies the independent validator
        for sol in solutions:
            report = validate_timetable(instance, sol)
            assert report.is_valid is True
            assert len(report.violations) == 0

    def test_oracle_on_impossible_proves_unsat(self):
        draft = load_sample("impossible")
        instance = instance_from_draft(draft)
        problem = build_csp(instance)

        solutions = find_all_solutions(problem)
        assert len(solutions) == 0, "Impossible instance must have 0 solutions"
        assert is_satisfiable(problem) is False
        assert count_solutions(problem) == 0

    def test_oracle_solution_limit(self):
        draft = load_sample("multi_solution")
        instance = instance_from_draft(draft)
        problem = build_csp(instance)

        total_solutions = count_solutions(problem)
        assert total_solutions > 1, "multi_solution should have multiple solutions"

        # Ask for at most 1 solution
        limited = find_all_solutions(problem, limit=1)
        assert len(limited) == 1
        assert count_solutions(problem, limit=1) == 1

    def test_oracle_on_feasible_obvious(self):
        draft = load_sample("feasible_obvious")
        instance = instance_from_draft(draft)
        problem = build_csp(instance)

        solutions = find_all_solutions(problem)
        assert len(solutions) > 0
        for sol in solutions:
            assert validate_timetable(instance, sol).is_valid is True
