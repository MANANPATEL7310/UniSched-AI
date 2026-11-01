"""Reversible domain state with trail-based backtracking."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csp.problem import CSPProblem


class DomainState:
    """Manages the alive status of domain values for CSP variables with backtrackable trail undo."""

    def __init__(self, problem: CSPProblem) -> None:
        self.alive: dict[str, list[bool]] = {
            s: [True] * len(problem.domains[s]) for s in problem.variables
        }
        self.size: dict[str, int] = {
            s: len(problem.domains[s]) for s in problem.variables
        }
        self._trail: list[tuple[str, int]] = []

    def remove(self, s: str, i: int) -> None:
        """Mark value index `i` of variable `s` as pruned.

        Precondition: alive[s][i] must be True.
        """
        if not self.alive[s][i]:
            return
        self.alive[s][i] = False
        self.size[s] -= 1
        self._trail.append((s, i))

    def checkpoint(self) -> int:
        """Return the current trail position (mark) for later backtracking."""
        return len(self._trail)

    def restore(self, mark: int) -> None:
        """Backtrack trail changes back to the given mark, restoring pruned values."""
        while len(self._trail) > mark:
            s, i = self._trail.pop()
            self.alive[s][i] = True
            self.size[s] += 1

    def alive_indices(self, s: str) -> list[int]:
        """Return currently alive value indices for variable `s` in original sorted order."""
        return [i for i, is_alive in enumerate(self.alive[s]) if is_alive]

    def snapshot(self) -> dict[str, tuple[bool, ...]]:
        """Return an immutable snapshot of all alive states, used for verification and testing."""
        return {s: tuple(is_alive) for s, is_alive in self.alive.items()}

    def removed_since(self, mark: int) -> set[str]:
        """Return the set of variables that had at least one value pruned since `mark`."""
        return {s for s, _ in self._trail[mark:]}
