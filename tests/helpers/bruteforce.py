"""Brute-force oracle for small instances (<= 8 sessions).

Enumerates the Cartesian product of variable domains with early pruning using
precomputed occupancy keys. Used exclusively as an oracle in test suites.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from models.assignment import Assignment

if TYPE_CHECKING:
    from csp.problem import CSPProblem


def find_all_solutions(problem: CSPProblem) -> list[dict[str, Assignment]]:
    """Enumerate all valid assignments {session_id: Assignment} for small problems."""
    variables = list(problem.variables)
    keys = problem.keys
    domains = problem.domains
    solutions: list[dict[str, Assignment]] = []

    def backtrack(idx: int, used_keys: set, current: dict[str, Assignment]) -> None:
        if idx == len(variables):
            solutions.append(dict(current))
            return

        sid = variables[idx]
        for val_idx, val_keys in enumerate(keys[sid]):
            if used_keys.isdisjoint(val_keys):
                candidate = domains[sid][val_idx]
                current[sid] = Assignment(
                    day=candidate.day,
                    start_slot=candidate.start_slot,
                    room_id=candidate.room_id,
                )
                backtrack(idx + 1, used_keys | val_keys, current)
                del current[sid]

    backtrack(0, set(), {})
    return solutions
