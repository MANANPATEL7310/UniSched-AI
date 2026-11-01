"""Brute-force oracle for small instances (<= 8 sessions).

Enumerates the Cartesian product of variable domains with early pruning using
precomputed occupancy keys. Used exclusively as a test oracle for correctness
and completeness cross-checking against CSP solvers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from models.assignment import Assignment

if TYPE_CHECKING:
    from csp.problem import CSPProblem


def find_all_solutions(
    problem: CSPProblem, limit: int | None = None
) -> list[dict[str, Assignment]]:
    """Enumerate valid assignments {session_id: Assignment} for small problems.

    Args:
        problem: CSPProblem instance with variables, domains, and keys.
        limit: Optional maximum number of solutions to collect before stopping.

    Returns:
        List of assignment dictionaries satisfying all hard binary/unary constraints.
    """
    variables = list(problem.variables)
    if not variables:
        return []

    keys = problem.keys
    domains = problem.domains
    solutions: list[dict[str, Assignment]] = []

    def backtrack(idx: int, used_keys: set, current: dict[str, Assignment]) -> None:
        if limit is not None and len(solutions) >= limit:
            return

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

                if limit is not None and len(solutions) >= limit:
                    return

    backtrack(0, set(), {})
    return solutions


def count_solutions(problem: CSPProblem, limit: int | None = None) -> int:
    """Count the number of valid solutions for a small problem."""
    return len(find_all_solutions(problem, limit=limit))


def is_satisfiable(problem: CSPProblem) -> bool:
    """Return True if at least one conflict-free solution exists, False otherwise."""
    return len(find_all_solutions(problem, limit=1)) > 0
