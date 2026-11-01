"""CSP constraint functions: unary checks and occupancy keys."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.assignment import Assignment
    from models.instance import SchedulingInstance
    from models.session import ClassSession

OccupancyKey = tuple[str, str, int]


def unary_ok(inst: SchedulingInstance, session: ClassSession, a: Assignment) -> bool:
    """Check if value assignment `a` is allowed for `session` under all unary constraints.

    Unary rules:
    1. 0 <= a.day < D and 0 <= a.start_slot < S; room exists in inst.rooms.
    2. a.start_slot + session.duration_slots <= S (must fit within the day).
    3. room.room_type in session.room_types.
    4. room.capacity >= session.required_capacity.
    5. For each slot j in [start .. start + duration - 1]:
       (day, j) not in teacher.unavailable and not in room.unavailable.
    6. If session.fixed is set: a == session.fixed.
    """
    grid = inst.grid

    # 1. Bounds check and room existence
    if not (0 <= a.day < grid.num_days):
        return False
    if not (0 <= a.start_slot < grid.slots_per_day):
        return False
    if a.room_id not in inst.rooms:
        return False

    # 2. Fits inside the day without day overflow
    dur = session.duration_slots
    if a.start_slot + dur > grid.slots_per_day:
        return False

    room = inst.rooms[a.room_id]

    # 3. Room type compatibility
    if room.room_type not in session.room_types:
        return False

    # 4. Room capacity sufficiency
    if room.capacity < session.required_capacity:
        return False

    # 5. Unavailability check for all occupied slots
    teacher = inst.teachers.get(session.teacher_id)
    teacher_unavail = teacher.unavailable if teacher is not None else frozenset()
    room_unavail = room.unavailable

    for j in range(dur):
        slot_coord = (a.day, a.start_slot + j)
        if slot_coord in teacher_unavail:
            return False
        if slot_coord in room_unavail:
            return False

    # 6. Fixed assignment requirement
    if session.fixed is not None and a != session.fixed:
        return False

    return True


def occupancy_keys(
    session: ClassSession, a: Assignment, slots_per_day: int
) -> frozenset[OccupancyKey]:
    """Compute the set of resource-slot occupancy keys for a session assignment.

    Format:
    - ("T", teacher_id, abs_slot)
    - ("D", division_id, abs_slot)
    - ("R", room_id, abs_slot)

    Two assignments clash if and only if their occupancy key sets are not disjoint.
    """
    keys: set[OccupancyKey] = set()
    base_abs = a.day * slots_per_day + a.start_slot

    for j in range(session.duration_slots):
        abs_slot = base_abs + j
        keys.add(("T", session.teacher_id, abs_slot))
        keys.add(("D", session.division_id, abs_slot))
        keys.add(("R", a.room_id, abs_slot))

    return frozenset(keys)
