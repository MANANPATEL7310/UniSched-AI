"""Variable and value selection heuristics for CSP search: MRV, Degree, and LCV."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csp.backtracking import _Ctx


def count_legal(ctx: _Ctx, sid: str) -> int:
    """Count alive values of unassigned variable `sid` that are consistent with currently used keys."""
    keys_s = ctx.problem.keys[sid]
    return sum(
        1
        for i in ctx.state.alive_indices(sid)
        if ctx.disjoint(keys_s[i], ctx.used)
    )


def select_variable(ctx: _Ctx) -> str:
    """Select the next unassigned variable to instantiate using MRV, Degree, and deterministic tie-breaking.

    Tie-break order:
    1. Minimum Remaining Values (MRV): fewest legal options remaining.
    2. Degree heuristic: most unassigned neighbors sharing resource keys.
    3. Alphabetical tie-break: smallest session_id.
    """
    unassigned = [s for s in ctx.problem.variables if s not in ctx.assignment]
    if not unassigned:
        raise RuntimeError("No unassigned variables remaining")

    if not (ctx.config.use_mrv or ctx.config.use_degree):
        # Baseline order: canonical sorted variable sequence (Config A)
        return unassigned[0]

    # MRV: Fewest legal values
    if ctx.config.use_mrv:
        # Precompute and cache legal counts
        legal_counts: dict[str, int] = {}
        for s in unassigned:
            if ctx.propagating:
                legal_counts[s] = ctx.state.size[s]
            else:
                legal_counts[s] = count_legal(ctx, s)

        min_val = min(legal_counts.values())
        ties = [s for s in unassigned if legal_counts[s] == min_val]
    else:
        ties = unassigned

    # Degree heuristic tie-break: max unassigned neighbors
    if ctx.config.use_degree and len(ties) > 1:
        deg = lambda s: sum(
            1 for n in ctx.problem.neighbors[s] if n not in ctx.assignment
        )
        max_deg = max(deg(s) for s in ties)
        ties = [s for s in ties if deg(s) == max_deg]

    # Final deterministic tie-break: lexicographically smallest session_id
    return min(ties)


def lcv_score(ctx: _Ctx, sid: str, i: int) -> int:
    """Calculate the Least Constraining Value (LCV) penalty score for value `i` of variable `sid`.

    Returns the count of legal values in unassigned neighbor variables that would be ruled out
    if `(sid, i)` were assigned. Lower score = less constraining.
    """
    seen: set[tuple[str, int]] = set()
    problem = ctx.problem
    state = ctx.state
    assignment = ctx.assignment
    propagating = ctx.propagating
    used = ctx.used

    for k in problem.keys[sid][i]:
        for s2, i2 in problem.key_index[k]:
            if s2 == sid or s2 in assignment or (s2, i2) in seen:
                continue
            if state.alive[s2][i2] and (
                propagating or ctx.disjoint(problem.keys[s2][i2], used)
            ):
                seen.add((s2, i2))

    return len(seen)


def order_values(ctx: _Ctx, sid: str) -> list[int]:
    """Order candidate domain indices for variable `sid`.

    If LCV is disabled: returns alive values in original sorted domain order.
    If LCV is enabled: orders legal values by ascending conflict score (least constraining first).
    Ties are broken deterministically by smaller original domain index.
    """
    alive = ctx.state.alive_indices(sid)
    if not ctx.config.use_lcv:
        return alive

    # Pre-filter to values that are consistent with currently assigned variables
    legal = [
        i
        for i in alive
        if ctx.propagating or ctx.disjoint(ctx.problem.keys[sid][i], ctx.used)
    ]

    scored = [(lcv_score(ctx, sid, i), i) for i in legal]
    # Sort by score ascending, breaking ties by value index i ascending
    scored.sort(key=lambda pair: (pair[0], pair[1]))
    return [i for _, i in scored]
