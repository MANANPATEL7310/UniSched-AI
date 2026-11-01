"""Tests for FastAPI HTTP endpoints (api/main.py, routers/samples.py, routers/instances.py)."""
from __future__ import annotations

import copy
import pytest
from fastapi.testclient import TestClient

from api.main import app
from data.loader import load_sample

client = TestClient(app)


def test_health_endpoints():
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert res1.json() == {"status": "ok", "version": "1.0"}

    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert res2.json() == {"status": "ok", "version": "1.0"}


def test_get_samples_list():
    res = client.get("/api/samples")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    names = [s["name"] for s in data]
    assert "tiny" in names


def test_get_sample_tiny():
    res = client.get("/api/samples/tiny")
    assert res.status_code == 200
    draft = res.json()
    assert draft["name"] == "tiny"
    assert "days" in draft
    assert "slots" in draft
    assert "teachers" in draft


def test_get_sample_path_traversal():
    res = client.get("/api/samples/..%2Fetc")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "SAMPLE_NOT_FOUND"


def test_validate_valid_draft():
    draft = load_sample("tiny")
    res = client.post("/api/instances/validate", json=draft)
    assert res.status_code == 200
    body = res.json()
    assert body["parse_error"] is None
    assert len(body["issues"]) == 0
    assert body["summary"] == {
        "courses": 3,
        "teachers": 3,
        "rooms": 3,
        "divisions": 2,
        "sessions": 5,
    }


def test_validate_unknown_teacher():
    draft = load_sample("tiny")
    draft["courses"][0]["teacher_id"] = "T_UNKNOWN"
    res = client.post("/api/instances/validate", json=draft)
    assert res.status_code == 200
    body = res.json()
    assert body["parse_error"] is None
    issues = body["issues"]
    assert any(i["code"] == "UNKNOWN_TEACHER" and "T_UNKNOWN" in i["message"] for i in issues)


def test_validate_bad_slot_string_gives_parse_error():
    draft = load_sample("tiny")
    draft["teachers"][0]["unavailable_slots"] = ["Mon@09:30"]
    res = client.post("/api/instances/validate", json=draft)
    assert res.status_code == 200
    body = res.json()
    assert body["parse_error"] is not None
    assert "Mon@09:30" in body["parse_error"]
    assert body["summary"] is None


def test_validate_missing_field_gives_422():
    draft = load_sample("tiny")
    del draft["rooms"]
    res = client.post("/api/instances/validate", json=draft)
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "BAD_REQUEST"


def test_upload_csv_valid():
    files = [
        ("files", ("days.csv", b"day_name\nMon\nTue\n", "text/csv")),
        ("files", ("slots.csv", b"start_time,end_time\n09:00,10:00\n10:00,11:00\n", "text/csv")),
        ("files", ("teachers.csv", b"teacher_id,teacher_name,unavailable_slots,preferred_slots,max_daily_sessions\nT01,Dr. Rao,Mon@09:00,,3\n", "text/csv")),
        ("files", ("courses.csv", b"course_id,course_name,teacher_id,sessions_per_week,duration_slots,room_types,eligible_divisions\nFAI,AI,T01,1,1,lecture,A\n", "text/csv")),
        ("files", ("divisions.csv", b"division_id,division_name,student_count,enrolled_courses\nA,Div A,50,FAI\n", "text/csv")),
        ("files", ("rooms.csv", b"room_id,room_name,room_type,capacity,unavailable_slots\nR101,Room 101,lecture,60,\n", "text/csv")),
        ("files", ("fixed_assignments.csv", b"session_id,day_name,start_time,room_id\nFAI|A|1,Mon,10:00,R101\n", "text/csv")),
    ]
    res = client.post("/api/instances/upload-csv", files=files)
    assert res.status_code == 200
    draft = res.json()
    assert draft["days"] == ["Mon", "Tue"]
    assert len(draft["teachers"]) == 1


def test_upload_csv_text_in_number_column():
    files = [
        ("files", ("days.csv", b"day_name\nMon\nTue\n", "text/csv")),
        ("files", ("slots.csv", b"start_time,end_time\n09:00,10:00\n10:00,11:00\n", "text/csv")),
        ("files", ("teachers.csv", b"teacher_id,teacher_name,unavailable_slots,preferred_slots,max_daily_sessions\nT01,Dr. Rao,Mon@09:00,,3\n", "text/csv")),
        ("files", ("courses.csv", b"course_id,course_name,teacher_id,sessions_per_week,duration_slots,room_types,eligible_divisions\nFAI,AI,T01,1,1,lecture,A\n", "text/csv")),
        ("files", ("divisions.csv", b"division_id,division_name,student_count,enrolled_courses\nA,Div A,50,FAI\n", "text/csv")),
        ("files", ("rooms.csv", b"room_id,room_name,room_type,capacity,unavailable_slots\nR101,Room 101,lecture,abc,\n", "text/csv")),
    ]
    res = client.post("/api/instances/upload-csv", files=files)
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "DATA_LOAD_ERROR"
    assert "rooms.csv row 2" in body["error"]["message"]


def test_post_runs_tiny_and_poll_done():
    import time

    draft = load_sample("tiny")
    payload = {
        "draft": draft,
        "config": {"algorithm": "A", "timeout_s": 10.0, "node_limit": None},
    }
    res = client.post("/api/runs", json=payload)
    assert res.status_code == 202
    run_id = res.json()["run_id"]
    assert isinstance(run_id, str)

    # Poll until done
    for _ in range(50):
        poll = client.get(f"/api/runs/{run_id}")
        assert poll.status_code == 200
        data = poll.json()
        if data["state"] == "done":
            break
        time.sleep(0.05)

    assert data["state"] == "done"
    outcome = data["outcome"]
    assert outcome is not None
    assert outcome["status"] == "SOLVED"
    assert outcome["is_valid"] is True
    assert outcome["num_sessions"] == 5
    assert len(outcome["timetable"]["entries"]) == 5

    # Test CSV download endpoint
    csv_res = client.get(f"/api/runs/{run_id}/timetable.csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["Content-Type"]
    csv_text = csv_res.text
    assert "Day,Start,End,Duration (slots),Course,Teacher,Division,Room,Session ID" in csv_text
    assert "FAI|A|1" in csv_text


def test_post_runs_with_input_errors():
    draft = load_sample("tiny")
    draft["courses"][0]["teacher_id"] = "UNKNOWN_TEACHER"
    payload = {
        "draft": draft,
        "config": {"algorithm": "A", "timeout_s": 10.0, "node_limit": None},
    }
    res = client.post("/api/runs", json=payload)
    assert res.status_code == 409
    body = res.json()
    assert body["error"]["code"] == "INPUT_ERRORS"
    assert any(i["code"] == "UNKNOWN_TEACHER" for i in body["error"]["details"])


def test_cancel_run_endpoint():
    draft = load_sample("tiny")
    payload = {
        "draft": draft,
        "config": {"algorithm": "A", "timeout_s": 10.0, "node_limit": None},
    }
    res = client.post("/api/runs", json=payload)
    run_id = res.json()["run_id"]

    cancel_res = client.post(f"/api/runs/{run_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json() == {"ok": True}


def test_get_run_not_found():
    res = client.get("/api/runs/nonexistent_id")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

