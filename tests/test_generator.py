"""Unit and integration tests for synthetic instance generator and API router."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from csp.backtracking import solve
from csp.problem import build_csp
from csp.result import PRESETS as SOLVER_PRESETS, SearchStatus
from data.generator import PRESETS, GeneratorConfig, generate_instance
from models.assignment import Assignment
from scheduling.timetable_validator import validate_timetable

client = TestClient(app)


def test_generator_determinism():
    cfg1 = GeneratorConfig(name="det_test", seed=123)
    cfg2 = GeneratorConfig(name="det_test", seed=123)
    cfg_diff = GeneratorConfig(name="det_test", seed=456)

    inst1 = generate_instance(cfg1)
    inst2 = generate_instance(cfg2)
    inst_diff = generate_instance(cfg_diff)

    assert inst1.name == inst2.name
    assert len(inst1.sessions) == len(inst2.sessions)
    assert inst1.meta["planted_solution"] == inst2.meta["planted_solution"]

    # Different seeds should produce different solutions or different sessions
    assert inst1.meta["planted_solution"] != inst_diff.meta["planted_solution"]


@pytest.mark.parametrize("preset_name", ["small", "medium", "large"])
def test_preset_planted_solution_validity(preset_name: str):
    cfg = PRESETS[preset_name]
    inst = generate_instance(cfg)

    assert len(inst.sessions) > 0
    assert inst.meta["num_sessions"] == len(inst.sessions)
    assert "planted_solution" in inst.meta

    # Reconstruct assignment from planted_solution
    plant_coords = inst.meta["planted_solution"]
    assert len(plant_coords) == len(inst.sessions)

    assignment = {
        sid: Assignment(day=coord[0], start_slot=coord[1], room_id=coord[2])
        for sid, coord in plant_coords.items()
    }

    report = validate_timetable(inst, assignment)
    assert report.is_valid is True, f"Planted solution for {preset_name} had violations: {report.violations}"
    assert len(report.violations) == 0


def test_solver_solves_generated_small():
    cfg = GeneratorConfig(name="solver_test", num_days=3, slots_per_day=4, num_divisions=2, num_teachers=3, num_courses=3, num_rooms=3, tightness=0.4, seed=7)
    inst = generate_instance(cfg)
    prob = build_csp(inst)

    res = solve(prob, SOLVER_PRESETS["B"])
    assert res.status == SearchStatus.SOLVED
    assert res.assignment is not None

    report = validate_timetable(inst, res.assignment)
    assert report.is_valid is True


def test_api_generator_presets():
    res = client.get("/api/generator/presets")
    assert res.status_code == 200
    data = res.json()
    assert "small" in data
    assert "medium" in data
    assert "large" in data
    assert data["small"]["num_days"] == 5
    assert data["small"]["num_rooms"] == 4


def test_api_generate_instance_and_validate():
    payload = {
        "name": "api_test",
        "num_days": 5,
        "slots_per_day": 6,
        "num_divisions": 3,
        "num_teachers": 4,
        "num_courses": 6,
        "num_rooms": 4,
        "availability_density": 0.3,
        "tightness": 0.5,
        "seed": 42,
    }

    res = client.post("/api/instances/generate", json=payload)
    assert res.status_code == 200
    draft = res.json()
    assert draft["name"] == "api_test"
    assert len(draft["days"]) == 5
    assert len(draft["slots"]) == 6
    assert len(draft["rooms"]) == 4

    # Verify planted solution is not leaked in client-facing draft
    assert "meta" not in draft
    assert "planted_solution" not in draft

    # Verify generated draft passes /instances/validate endpoint with 0 issues
    val_res = client.post("/api/instances/validate", json=draft)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["parse_error"] is None
    assert len(val_data["issues"]) == 0
    assert val_data["summary"]["sessions"] > 0
