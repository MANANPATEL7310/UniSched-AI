"""AC-3 arc consistency algorithm and root AC-3 propagation."""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from csp.backtracking import _Ctx
    from csp.problem import CSPProblem


def revise(ctx: _Ctx, xi: str, xj: str, count_as: str = "search") -> bool:
    """Revise the domain of variable `xi` with respect to neighbor `xj`.

    Removes any value `v` in domain(xi) for which there is no compatible alive
    value in domain(xj) (i.e. where all alive values of xj conflict on occupancy keys).
    Returns True if at least one value was removed from `xi`, False otherwise.
    """
    removed = False
    st = ctx.state
    p = ctx.problem
    keys_xi = p.keys[xi]
    keys_xj = p.keys[xj]
    alive_xj = st.alive_indices(xj)

    # We iterate over alive_indices(xi) copy because st.remove mutates alive
    for i in st.alive_indices(xi):
        ki = keys_xi[i]
        # Check if there exists at least one alive value in xj compatible with (xi, i)
        has_support = False
        for j in alive_xj:
            if ctx.disjoint(ki, keys_xj[j]):
                has_support = True
                break

        if not has_support:
            st.remove(xi, i)
            if count_as == "root":
                ctx.metrics.root_pruned += 1
            else:
                ctx.metrics.values_pruned += 1
            removed = True

    return removed


def ac3(
    ctx: _Ctx,
    arcs: Iterable[tuple[str, str]],
    count_as: str = "search",
) -> bool:
    """Enforce arc consistency over the given set of directed arcs.

    Maintains a worklist of arcs (queue). Whenever revise(xi, xj) prunes values from xi:
    - If xi's domain becomes empty, returns False immediately (wipeout).
    - Otherwise, re-enqueues all incoming arcs (xk, xi) for all unassigned neighbors xk != xj.
    Returns True if all arcs are made arc-consistent without any domain wipeout.
    """
    queue: deque[tuple[str, str]] = deque(arcs)
    queued: set[tuple[str, str]] = set(queue)
    assignment = ctx.assignment
    neighbors = ctx.problem.neighbors
    state = ctx.state

    while queue:
        xi, xj = queue.popleft()
        queued.discard((xi, xj))

        if revise(ctx, xi, xj, count_as=count_as):
            if state.size[xi] == 0:
                ctx.metrics.domain_wipeouts += 1
                return False

            for xk in neighbors[xi]:
                if xk != xj and xk not in assignment and (xk, xi) not in queued:
                    queue.append((xk, xi))
                    queued.add((xk, xi))

    return True


def root_arcs(problem: CSPProblem) -> list[tuple[str, str]]:
    """Return all directed arcs between all pairs of neighboring variables."""
    return [
        (a, b)
        for a in problem.variables
        for b in sorted(problem.neighbors[a])
    ]


def ac3_root(ctx: _Ctx) -> bool:
    """Perform root-level AC-3 arc consistency preprocessing before search begins."""
    return ac3(ctx, root_arcs(ctx.problem), count_as="root")

