"""CSPProblem representation and problem builder."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from csp.constraints import OccupancyKey, occupancy_keys
from csp.domains import build_domains

if TYPE_CHECKING:
    from models.assignment import Assignment
    from models.instance import SchedulingInstance


@dataclass(frozen=True)
class CSPProblem:
    """Immutable compiled representation of the CSP for a scheduling instance."""

    instance: SchedulingInstance
    variables: tuple[str, ...]
    domains: dict[str, list[Assignment]]
    keys: dict[str, list[frozenset[OccupancyKey]]]
    key_index: dict[OccupancyKey, list[tuple[str, int]]]
    neighbors: dict[str, frozenset[str]]
    slots_per_day: int
    root_wipeout: str | None

    def conflicts(self, s1: str, i1: int, s2: str, i2: int) -> bool:
        """Check if value i1 of variable s1 conflicts with value i2 of variable s2."""
        return not self.keys[s1][i1].isdisjoint(self.keys[s2][i2])


def build_csp(inst: SchedulingInstance) -> CSPProblem:
    """Compile a SchedulingInstance into a CSPProblem structure with precomputed keys and indices."""
    domains = build_domains(inst)
    variables = tuple(sorted(domains.keys()))
    slots_per_day = inst.grid.slots_per_day

    keys: dict[str, list[frozenset[OccupancyKey]]] = {}
    key_index: dict[OccupancyKey, list[tuple[str, int]]] = defaultdict(list)
    session_map = {s.session_id: s for s in inst.sessions}

    for s in variables:
        sess = session_map[s]
        s_keys_list = [occupancy_keys(sess, v, slots_per_day) for v in domains[s]]
        keys[s] = s_keys_list
        for i, ks in enumerate(s_keys_list):
            for k in ks:
                key_index[k].append((s, i))

    sessions_by_key = {k: {s for s, _ in lst} for k, lst in key_index.items()}
    neighbors: dict[str, frozenset[str]] = {}
    for s in variables:
        all_s_keys = {k for ks in keys[s] for k in ks}
        shared_sessions: set[str] = set()
        for k in all_s_keys:
            shared_sessions.update(sessions_by_key.get(k, ()))
        shared_sessions.discard(s)
        neighbors[s] = frozenset(shared_sessions)

    root_wipeout: str | None = None
    for s in variables:
        if len(domains[s]) == 0:
            root_wipeout = s
            break

    return CSPProblem(
        instance=inst,
        variables=variables,
        domains=domains,
        keys=keys,
        key_index=dict(key_index),
        neighbors=neighbors,
        slots_per_day=slots_per_day,
        root_wipeout=root_wipeout,
    )
