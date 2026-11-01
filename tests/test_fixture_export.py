"""Tests for scripts/export_fixture_outcome.py."""
from __future__ import annotations

import json
from pathlib import Path

from api.schemas import RunOutcomeModel
from scripts.export_fixture_outcome import export_fixture


def test_export_fixture_outcome_generates_valid_run_outcome(tmp_path):
    target = tmp_path / "test_outcome.json"
    dto = export_fixture(out_path=target)

    assert target.exists()
    assert dto["status"] == "SOLVED"
    assert dto["algorithm"] == "A"
    assert dto["is_valid"] is True
    assert dto["num_sessions"] == 5
    assert len(dto["timetable"]["entries"]) == 5

    # Verify Pydantic validation passes on the generated DTO
    model = RunOutcomeModel.model_validate(dto)
    assert model.status == "SOLVED"
    assert model.timetable is not None
    assert len(model.timetable.entries) == 5


def test_bundled_frontend_fixture_exists_and_is_valid():
    fixture_path = Path("frontend/src/tests/fixtures/tiny_outcome.json")
    assert fixture_path.exists(), "frontend fixture tiny_outcome.json must exist"

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    model = RunOutcomeModel.model_validate(data)
    assert model.status == "SOLVED"
    assert model.is_valid is True
