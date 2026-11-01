"""Tests for soft-constraint local optimization."""
from __future__ import annotations

import pytest
from data.loader import instance_from_draft, load_sample
from scheduling.scheduler import generate_timetable
from scheduling.soft_constraints import SoftWeights, soft_penalty
from scheduling.soft_improvement import improve_soft_constraints


def test_soft_improvement_maintains_hard_validity() -> None:
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.status.value == "SOLVED"
    assert run_outcome.timetable is not None

    outcome = improve_soft_constraints(
        instance=inst,
        timetable=run_outcome.timetable,
        max_steps=50,
        time_limit_s=2.0,
    )

    assert outcome.validation.is_valid
    assert outcome.improved_penalty <= outcome.initial_penalty
    assert outcome.status in ("IMPROVED", "UNCHANGED")


def test_soft_improvement_rejects_invalid_timetable() -> None:
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.timetable is not None

    # Corrupt the timetable by assigning to an invalid slot
    corrupt_asgn = dict(run_outcome.timetable.assignment)
    first_sid = next(iter(corrupt_asgn.keys()))
    from models.assignment import Assignment
    corrupt_asgn[first_sid] = Assignment(day=99, start_slot=99, room_id="NO_ROOM")
    from models.timetable import Timetable
    corrupt_tt = Timetable(inst, corrupt_asgn)

    with pytest.raises(ValueError, match="Cannot optimize soft constraints on an invalid timetable"):
        improve_soft_constraints(inst, corrupt_tt)
