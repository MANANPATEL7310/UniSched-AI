"""Domain generation for CSP variables."""
from __future__ import annotations

from typing import TYPE_CHECKING

from csp.constraints import unary_ok
from models.assignment import Assignment

if TYPE_CHECKING:
    from models.instance import SchedulingInstance


def build_domains(inst: SchedulingInstance) -> dict[str, list[Assignment]]:
    """Build the unary-filtered assignment domain for every session in inst.sessions.

    Domains are sorted ascending by (day, start_slot, room_id).
    If a session has a fixed assignment, its domain contains only that assignment
    (if valid under unary constraints) or is empty.
    """
    domains: dict[str, list[Assignment]] = {}
    num_days = inst.grid.num_days
    slots_per_day = inst.grid.slots_per_day
    room_ids = sorted(inst.rooms.keys())

    for sess in inst.sessions:
        if sess.fixed is not None:
            cand = [sess.fixed] if unary_ok(inst, sess, sess.fixed) else []
        else:
            cand = [
                Assignment(day=d, start_slot=t, room_id=r)
                for d in range(num_days)
                for t in range(slots_per_day)
                for r in room_ids
                if unary_ok(inst, sess, Assignment(day=d, start_slot=t, room_id=r))
            ]
        domains[sess.session_id] = sorted(cand)

    return domains
