"""Maintaining Arc Consistency (MAC) propagation for CSP search (Config D)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from csp.ac3 import ac3
from csp.forward_checking import forward_check

if TYPE_CHECKING:
    from csp.backtracking import _Ctx


def mac_propagate(ctx: _Ctx, sid: str, i: int) -> bool:
    """Enforce Maintaining Arc Consistency (MAC) after assigning `(sid, i)`.

    Two-stage propagation:
    1. Forward checking: prune conflicting values from unassigned immediate neighbors.
       If any neighbor domain wipes out, returns False immediately.
    2. Arc consistency (AC-3): collects all variables that lost values during Step 1,
       builds directed arcs (xk, xc) from unassigned neighbors, and propagates arc
       consistency until fixed point or domain wipeout.
    """
    mark = len(ctx.state._trail)

    # Step 1: Forward check immediate neighbors
    if not forward_check(ctx, sid, i):
        return False

    # Step 2: Propagate consequences with AC-3 on changed variables
    changed = ctx.state.removed_since(mark)
    if not changed:
        return True

    assignment = ctx.assignment
    neighbors = ctx.problem.neighbors

    arcs = [
        (xk, xc)
        for xc in changed
        for xk in neighbors[xc]
        if xk not in assignment and xk != xc
    ]

    if not arcs:
        return True

    return ac3(ctx, arcs, count_as="search")

