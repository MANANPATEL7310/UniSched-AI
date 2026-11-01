"""Forward checking propagation for CSP search (Config C)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csp.backtracking import _Ctx


def forward_check(ctx: _Ctx, sid: str, i: int) -> bool:
    """Prune conflicting values from domains of unassigned neighbor variables.

    When `(sid, i)` is assigned, iterates over all precomputed occupancy keys in `keys[sid][i]`.
    For each key, looks up all conflicting candidate values `(s2, i2)` via `key_index[k]`.
    If `s2` is unassigned and `i2` is currently alive, removes `(s2, i2)` from `DomainState`.
    If any neighbor's domain is wiped out completely (size drops to 0), returns `False`
    immediately so the search caller can backtrack and restore its checkpoint.
    """
    st = ctx.state
    p = ctx.problem
    a = ctx.assignment

    for k in p.keys[sid][i]:
        for s2, i2 in p.key_index[k]:
            if s2 == sid or s2 in a or not st.alive[s2][i2]:
                continue
            st.remove(s2, i2)
            ctx.metrics.values_pruned += 1
            if st.size[s2] == 0:
                ctx.metrics.domain_wipeouts += 1
                return False  # Wipeout detected: fail-first

    return True
