"""Minimal-change timetable rescheduling and repair engine.

Provides automated conflict repair when a teacher or room becomes unavailable:
- Identifies directly affected sessions.
- Applies configurable locking policies: 'strict', 'relax_neighbors', or 'free'.
- Ranks candidate assignments for free sessions by distance from the original assignment.
- Progressively unlocks neighbor rings when 'relax_neighbors' is active.
- Computes comprehensive diffs and validates with the independent timetable validator.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from csp.backtracking import solve
from csp.constraints import OccupancyKey
from csp.problem import CSPProblem, build_csp
from csp.result import PRESETS, SearchConfig, SearchMetrics, SearchStatus
from models.assignment import Assignment
from models.instance import SchedulingInstance
from models.room import Room
from models.session import ClassSession
from models.teacher import Teacher
from models.timetable import Timetable
from scheduling.timetable_validator import ValidationReport, validate_timetable


@dataclass(frozen=True)
class TeacherUnavailableChange:
    """Disruption specifying that a teacher is unavailable at a given day and slot."""

    teacher_id: str
    day: int
    slot: int


@dataclass(frozen=True)
class RoomUnavailableChange:
    """Disruption specifying that a room is unavailable at a given day and slot."""

    room_id: str
    day: int
    slot: int


RepairChange = TeacherUnavailableChange | RoomUnavailableChange


@dataclass(frozen=True)
class SessionDiff:
    """Detailed record of how a session assignment changed during rescheduling."""

    session_id: str
    course_name: str
    division_name: str
    teacher_name: str
    old_day: int | None
    old_slot: int | None
    old_room_id: str | None
    new_day: int
    new_slot: int
    new_room_id: str
    change_type: Literal["UNCHANGED", "MOVED_SLOT", "MOVED_ROOM", "MOVED_BOTH", "NEWLY_ASSIGNED"]


@dataclass
class RescheduleOutcome:
    """Outcome of a minimal-change rescheduling operation."""

    status: str
    timetable: Timetable | None
    diff: list[SessionDiff]
    relaxed_locks: list[str]
    change_penalty: int
    validation: ValidationReport | None
    metrics: SearchMetrics
    message: str


def _order_csp_by_distance(
    problem: CSPProblem,
    old_assignments: dict[str, Assignment],
) -> CSPProblem:
    """Reorder domain values for free sessions by ascending disruption distance from old assignments."""
    new_domains: dict[str, list[Assignment]] = {}
    new_keys: dict[str, list[frozenset[OccupancyKey]]] = {}

    for s in problem.variables:
        dom = problem.domains[s]
        old_a = old_assignments.get(s)
        if old_a is not None and len(dom) > 1:
            paired = list(enumerate(dom))

            def dist_key(item: tuple[int, Assignment]) -> tuple[int, int, int, int, int]:
                orig_idx, v = item
                is_exact = 0 if (v.day == old_a.day and v.start_slot == old_a.start_slot and v.room_id == old_a.room_id) else 1
                same_day = 0 if v.day == old_a.day else 1
                slot_dist = abs(v.start_slot - old_a.start_slot)
                same_room = 0 if v.room_id == old_a.room_id else 1
                return (is_exact, same_day, slot_dist, same_room, orig_idx)

            paired.sort(key=dist_key)
            new_dom = [v for _, v in paired]
            orig_indices = [idx for idx, _ in paired]
            new_k = [problem.keys[s][idx] for idx in orig_indices]
            new_domains[s] = new_dom
            new_keys[s] = new_k
        else:
            new_domains[s] = dom
            new_keys[s] = problem.keys[s]

    new_key_index: dict[OccupancyKey, list[tuple[str, int]]] = defaultdict(list)
    for s in problem.variables:
        for i, ks in enumerate(new_keys[s]):
            for k in ks:
                new_key_index[k].append((s, i))

    return CSPProblem(
        instance=problem.instance,
        variables=problem.variables,
        domains=new_domains,
        keys=new_keys,
        key_index=new_key_index,
        neighbors=problem.neighbors,
        slots_per_day=problem.slots_per_day,
        root_wipeout=problem.root_wipeout,
    )


def _build_neighbor_graph(
    instance: SchedulingInstance,
    timetable: Timetable,
) -> dict[str, set[str]]:
    """Build resource-sharing adjacency graph between all class sessions."""
    graph: dict[str, set[str]] = defaultdict(set)
    sessions = list(instance.sessions)

    for i in range(len(sessions)):
        s1 = sessions[i]
        asgn1 = timetable.assignment.get(s1.session_id)
        for j in range(i + 1, len(sessions)):
            s2 = sessions[j]
            asgn2 = timetable.assignment.get(s2.session_id)
            share_resource = (
                s1.teacher_id == s2.teacher_id
                or s1.division_id == s2.division_id
                or (asgn1 and asgn2 and asgn1.room_id == asgn2.room_id)
            )
            if share_resource:
                graph[s1.session_id].add(s2.session_id)
                graph[s2.session_id].add(s1.session_id)

    return graph


def _compute_diff(
    instance: SchedulingInstance,
    old_assignment: dict[str, Assignment],
    new_assignment: dict[str, Assignment],
) -> tuple[list[SessionDiff], int]:
    """Compute difference table between old and new timetable assignments."""
    diff_list: list[SessionDiff] = []
    change_count = 0
    session_map = {s.session_id: s for s in instance.sessions}

    for sid, s in session_map.items():
        old_a = old_assignment.get(sid)
        new_a = new_assignment.get(sid)

        course = instance.courses.get(s.course_id)
        division = instance.divisions.get(s.division_id)
        teacher = instance.teachers.get(s.teacher_id)

        c_name = course.name if course else s.course_id
        d_name = division.name if division else s.division_id
        t_name = teacher.name if teacher else s.teacher_id

        if new_a is None:
            continue

        if old_a is None:
            change_type = "NEWLY_ASSIGNED"
            change_count += 1
        elif (
            old_a.day == new_a.day
            and old_a.start_slot == new_a.start_slot
            and old_a.room_id == new_a.room_id
        ):
            change_type = "UNCHANGED"
        elif old_a.day == new_a.day and old_a.start_slot == new_a.start_slot:
            change_type = "MOVED_ROOM"
            change_count += 1
        elif old_a.day == new_a.day and old_a.room_id == new_a.room_id:
            change_type = "MOVED_SLOT"
            change_count += 1
        else:
            change_type = "MOVED_BOTH"
            change_count += 1

        diff_list.append(
            SessionDiff(
                session_id=sid,
                course_name=c_name,
                division_name=d_name,
                teacher_name=t_name,
                old_day=old_a.day if old_a else None,
                old_slot=old_a.start_slot if old_a else None,
                old_room_id=old_a.room_id if old_a else None,
                new_day=new_a.day,
                new_slot=new_a.start_slot,
                new_room_id=new_a.room_id,
                change_type=change_type,
            )
        )

    # Sort diffs: changed first, then by day and slot
    diff_list.sort(key=lambda d: (0 if d.change_type != "UNCHANGED" else 1, d.new_day, d.new_slot, d.session_id))
    return diff_list, change_count


def reschedule(
    instance_old: SchedulingInstance,
    timetable_old: Timetable,
    change: RepairChange,
    locks_policy: Literal["strict", "relax_neighbors", "free"] = "relax_neighbors",
    timeout_s: float = 15.0,
) -> RescheduleOutcome:
    """Perform minimal-change rescheduling in response to an unavailability disruption.

    Args:
        instance_old: Base scheduling problem instance.
        timetable_old: Currently published solution timetable.
        change: The teacher or room unavailability perturbation.
        locks_policy: 'strict' (unaffected frozen), 'relax_neighbors' (progressive rings), or 'free'.
        timeout_s: Timeout per solve attempt.

    Returns:
        RescheduleOutcome containing new timetable, diff table, relaxed locks, and validation.
    """
    # 1. Build instance_new with the new unavailability constraint
    new_teachers = dict(instance_old.teachers)
    new_rooms = dict(instance_old.rooms)

    if isinstance(change, TeacherUnavailableChange):
        if change.teacher_id not in new_teachers:
            raise ValueError(f"Teacher '{change.teacher_id}' not found in instance.")
        old_t = new_teachers[change.teacher_id]
        updated_unavail = old_t.unavailable | {(change.day, change.slot)}
        new_teachers[change.teacher_id] = Teacher(
            teacher_id=old_t.teacher_id,
            name=old_t.name,
            unavailable=updated_unavail,
            preferred=old_t.preferred,
            max_daily_sessions=old_t.max_daily_sessions,
        )
    elif isinstance(change, RoomUnavailableChange):
        if change.room_id not in new_rooms:
            raise ValueError(f"Room '{change.room_id}' not found in instance.")
        old_r = new_rooms[change.room_id]
        updated_unavail = old_r.unavailable | {(change.day, change.slot)}
        new_rooms[change.room_id] = Room(
            room_id=old_r.room_id,
            name=old_r.name,
            room_type=old_r.room_type,
            capacity=old_r.capacity,
            unavailable=updated_unavail,
        )
    else:
        raise TypeError(f"Unsupported change type {type(change)}")

    instance_base = SchedulingInstance(
        name=instance_old.name,
        grid=instance_old.grid,
        teachers=new_teachers,
        rooms=new_rooms,
        divisions=instance_old.divisions,
        courses=instance_old.courses,
        sessions=instance_old.sessions,
        meta=dict(instance_old.meta),
    )

    # 2. Identify directly affected sessions
    session_map = {s.session_id: s for s in instance_old.sessions}
    affected: set[str] = set()

    for sid, asgn in timetable_old.assignment.items():
        sess = session_map.get(sid)
        if sess is None:
            continue
        covers_slot = asgn.day == change.day and asgn.start_slot <= change.slot < asgn.start_slot + sess.duration_slots
        if isinstance(change, TeacherUnavailableChange):
            if sess.teacher_id == change.teacher_id and covers_slot:
                affected.add(sid)
        elif isinstance(change, RoomUnavailableChange):
            if asgn.room_id == change.room_id and covers_slot:
                affected.add(sid)

    # If no session is affected, existing timetable is still fully valid
    if not affected:
        val = validate_timetable(instance_base, timetable_old)
        diff, penalty = _compute_diff(instance_base, timetable_old.assignment, timetable_old.assignment)
        return RescheduleOutcome(
            status="SOLVED",
            timetable=timetable_old,
            diff=diff,
            relaxed_locks=[],
            change_penalty=0,
            validation=val,
            metrics=SearchMetrics(),
            message="No scheduled sessions conflicted with the new unavailability. Timetable remains valid.",
        )

    # 3. Determine neighbor rings for progressive relaxation
    graph = _build_neighbor_graph(instance_base, timetable_old)
    ring0 = set(affected)
    ring1: set[str] = set()
    for s in ring0:
        ring1.update(graph.get(s, set()))
    ring1 -= ring0

    ring2: set[str] = set()
    for s in ring1:
        ring2.update(graph.get(s, set()))
    ring2 -= (ring0 | ring1)

    all_sids = set(session_map.keys())

    # Build relaxation tiers
    if locks_policy == "strict":
        tiers = [(ring0, "Strict lock: only directly affected sessions free")]
    elif locks_policy == "free":
        tiers = [(all_sids, "Free search: all session assignments open to change")]
    else:  # "relax_neighbors"
        tiers = [
            (ring0, "Ring 0: only directly affected sessions unlocked"),
            (ring0 | ring1, "Ring 1: expanded to resource-sharing neighbors"),
            (ring0 | ring1 | ring2, "Ring 2: expanded to secondary neighbors"),
            (all_sids, "Full unlock: all sessions unlocked"),
        ]

    # Solver configuration: use MAC + AC-3 for fastest completeness proofs
    cfg = SearchConfig(
        name="D",
        use_mrv=True,
        use_degree=True,
        use_lcv=True,
        use_ac3_root=True,
        use_mac=True,
        timeout_s=timeout_s,
    )

    last_metrics = SearchMetrics()
    for free_sessions, tier_desc in tiers:
        # Build sessions with fixed locks for non-free sessions
        new_sessions = []
        for s in instance_old.sessions:
            if s.session_id in free_sessions:
                new_s = ClassSession(
                    session_id=s.session_id,
                    course_id=s.course_id,
                    division_id=s.division_id,
                    teacher_id=s.teacher_id,
                    duration_slots=s.duration_slots,
                    room_types=s.room_types,
                    required_capacity=s.required_capacity,
                    fixed=None,
                )
            else:
                old_asgn = timetable_old.assignment.get(s.session_id)
                new_s = ClassSession(
                    session_id=s.session_id,
                    course_id=s.course_id,
                    division_id=s.division_id,
                    teacher_id=s.teacher_id,
                    duration_slots=s.duration_slots,
                    room_types=s.room_types,
                    required_capacity=s.required_capacity,
                    fixed=old_asgn,
                )
            new_sessions.append(new_s)

        trial_inst = SchedulingInstance(
            name=instance_base.name,
            grid=instance_base.grid,
            teachers=instance_base.teachers,
            rooms=instance_base.rooms,
            divisions=instance_base.divisions,
            courses=instance_base.courses,
            sessions=tuple(new_sessions),
            meta=dict(instance_base.meta),
        )

        base_problem = build_csp(trial_inst)
        if base_problem.root_wipeout is not None:
            continue

        problem = _order_csp_by_distance(base_problem, timetable_old.assignment)
        res = solve(problem, cfg)
        last_metrics = res.metrics

        if res.status == SearchStatus.SOLVED and res.assignment is not None:
            new_timetable = Timetable(instance_base, res.assignment)
            val = validate_timetable(instance_base, new_timetable)
            diff, penalty = _compute_diff(instance_base, timetable_old.assignment, new_timetable.assignment)
            relaxed = sorted(list(free_sessions - affected))
            msg = (
                f"Repaired successfully ({tier_desc}). {penalty} session(s) moved; "
                f"{len(relaxed)} lock(s) relaxed."
            )
            return RescheduleOutcome(
                status="SOLVED",
                timetable=new_timetable,
                diff=diff,
                relaxed_locks=relaxed,
                change_penalty=penalty,
                validation=val,
                metrics=res.metrics,
                message=msg,
            )

        if res.status == SearchStatus.TIMEOUT:
            return RescheduleOutcome(
                status="TIMEOUT",
                timetable=None,
                diff=[],
                relaxed_locks=[],
                change_penalty=0,
                validation=None,
                metrics=last_metrics,
                message=f"Rescheduling timed out after {timeout_s}s during {tier_desc}.",
            )

    return RescheduleOutcome(
        status="INFEASIBLE_PROVEN",
        timetable=None,
        diff=[],
        relaxed_locks=[],
        change_penalty=0,
        validation=None,
        metrics=last_metrics,
        message="No conflict-free timetable exists under the new unavailability constraint even after relaxing all locks.",
    )
