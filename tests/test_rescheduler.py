"""Tests for minimal-change timetable rescheduling and conflict repair."""
from __future__ import annotations

from data.loader import instance_from_draft, load_sample
from models.assignment import Assignment
from models.timetable import Timetable
from scheduling.rescheduler import (
    RescheduleOutcome,
    RoomUnavailableChange,
    TeacherUnavailableChange,
    reschedule,
)
from scheduling.scheduler import generate_timetable


def test_reschedule_noop_when_no_conflict() -> None:
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.status.value == "SOLVED"
    assert run_outcome.timetable is not None

    teacher_id = next(iter(inst.teachers.keys()))
    # Pick a day outside the timetable grid or slot where teacher is free
    change = TeacherUnavailableChange(teacher_id=teacher_id, day=0, slot=2)
    # Check if Alice is teaching at Mon 09:00
    res = reschedule(inst, run_outcome.timetable, change, locks_policy="strict")
    assert res.status == "SOLVED"
    assert res.validation is not None
    assert res.validation.is_valid


def test_reschedule_repairs_teacher_unavailability_with_strict_lock() -> None:
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.status.value == "SOLVED"
    old_tt = run_outcome.timetable
    assert old_tt is not None

    entries = old_tt.entries()
    assert len(entries) > 0
    target = entries[0]

    # Disrupt target teacher at this exact day and start_slot
    change = TeacherUnavailableChange(
        teacher_id=target.teacher_id,
        day=target.day,
        slot=target.start_slot,
    )

    res = reschedule(inst, old_tt, change, locks_policy="relax_neighbors")
    assert res.status == "SOLVED"
    assert res.timetable is not None
    assert res.validation is not None
    assert res.validation.is_valid
    assert res.change_penalty >= 1

    # Verify that the affected session moved away from (target.day, target.start_slot)
    new_asgn = res.timetable.assignment[target.session_id]
    assert not (new_asgn.day == target.day and new_asgn.start_slot == target.start_slot)

    # Verify diff table contains the moved session
    diff_sids = {d.session_id for d in res.diff if d.change_type != "UNCHANGED"}
    assert target.session_id in diff_sids


def test_reschedule_repairs_room_unavailability() -> None:
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.status.value == "SOLVED"
    old_tt = run_outcome.timetable
    assert old_tt is not None

    entries = old_tt.entries()
    assert len(entries) > 0
    target = entries[0]

    change = RoomUnavailableChange(
        room_id=target.room_id,
        day=target.day,
        slot=target.start_slot,
    )

    res = reschedule(inst, old_tt, change, locks_policy="relax_neighbors")
    assert res.status == "SOLVED"
    assert res.timetable is not None
    assert res.validation is not None
    assert res.validation.is_valid
    assert res.change_penalty >= 1

    new_asgn = res.timetable.assignment[target.session_id]
    assert not (new_asgn.day == target.day and new_asgn.start_slot == target.start_slot and new_asgn.room_id == target.room_id)
