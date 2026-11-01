"""Export tiny sample solution outcome fixture for frontend testing and development."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path when running as a standalone script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.serializers import outcome_to_dto
from data.loader import instance_from_draft, load_sample
from models.assignment import Assignment
from models.timetable import Timetable
from scheduling.timetable_validator import validate_timetable


@dataclass
class DummyMetrics:
    nodes: int = 0
    attempts: int = 0
    backtracks: int = 0
    checks: int = 0
    values_pruned: int = 0
    root_pruned: int = 0
    domain_wipeouts: int = 0


@dataclass
class FixtureOutcome:
    status: str
    message: str
    is_valid: bool
    num_sessions: int
    metrics: DummyMetrics
    runtime_s: float
    build_s: float
    peak_memory_kb: float | None
    timetable: Timetable
    validation: Any
    soft: Any = None


def export_fixture(out_path: Path | str = "frontend/src/tests/fixtures/tiny_outcome.json") -> dict:
    """Generate and write RunOutcome JSON fixture for tiny sample."""
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)

    sol_path = Path("tests/fixtures/tiny_solution.json")
    sol_data = json.loads(sol_path.read_text(encoding="utf-8"))
    assignments = {
        sid: Assignment(day=int(v[0]), start_slot=int(v[1]), room_id=str(v[2]))
        for sid, v in sol_data["assignments"].items()
    }

    tt = Timetable(inst, assignments)
    val_report = validate_timetable(inst, assignments)

    outcome = FixtureOutcome(
        status="SOLVED",
        message="Solved successfully (hand-verified fixture)",
        is_valid=val_report.is_valid,
        num_sessions=len(inst.sessions),
        metrics=DummyMetrics(),
        runtime_s=0.012,
        build_s=0.003,
        peak_memory_kb=None,
        timetable=tt,
        validation=val_report,
        soft=None,
    )

    dto = outcome_to_dto(outcome, run_id="fixture-tiny-run", algorithm="A")

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dto, indent=2), encoding="utf-8")
    print(f"Exported fixture outcome to {target}")
    return dto


if __name__ == "__main__":
    export_fixture()
