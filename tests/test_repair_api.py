"""Integration tests for the /api/repair and /api/repair/improve-soft endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from data.loader import instance_from_draft, load_sample
from scheduling.scheduler import generate_timetable


def test_api_repair_endpoint() -> None:
    client = TestClient(app)
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.timetable is not None

    published_json = run_outcome.timetable.to_json_dict()
    entries = run_outcome.timetable.entries()
    target = entries[0]

    body = {
        "draft": draft,
        "published": published_json,
        "change": {
            "type": "teacher_unavailable",
            "entity_id": target.teacher_id,
            "day": target.day,
            "slot": target.start_slot,
        },
        "lock_policy": "relax_neighbors",
        "timeout_s": 10.0,
    }

    res = client.post("/api/repair", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SOLVED"
    assert data["change_penalty"] >= 1
    assert len(data["diff"]) > 0
    assert data["outcome"] is not None
    assert data["outcome"]["is_valid"] is True


def test_api_improve_soft_endpoint() -> None:
    client = TestClient(app)
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    run_outcome = generate_timetable(inst)
    assert run_outcome.timetable is not None

    published_json = run_outcome.timetable.to_json_dict()

    body = {
        "draft": draft,
        "published": published_json,
        "max_steps": 50,
        "time_limit_s": 2.0,
    }

    res = client.post("/api/repair/improve-soft", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("IMPROVED", "UNCHANGED")
    assert data["improved_penalty"] <= data["initial_penalty"]
    assert data["outcome"]["is_valid"] is True
