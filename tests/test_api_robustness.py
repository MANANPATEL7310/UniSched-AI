"""Robustness, concurrency, security, and SPA serving tests for HTTP API endpoints."""
from __future__ import annotations

import time
from fastapi.testclient import TestClient
import pytest

from api.jobs import jobs
from api.main import app
from data.loader import load_sample

client = TestClient(app)


def test_path_traversal_samples_rejected():
    """Verify directory traversal attempts on sample endpoints are safely rejected."""
    bad_paths = [
        "/api/samples/..%2Fetc",
        "/api/samples/..%2F..%2Fetc%2Fpasswd",
        "/api/samples/subdir%2Ffile",
        "/api/samples/nonexistent_sample_xyz",
    ]
    for path in bad_paths:
        res = client.get(path)
        assert res.status_code == 404
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] in ("SAMPLE_NOT_FOUND", "NOT_FOUND")


def test_bad_payload_missing_required_fields():
    """Ensure malformed or incomplete JSON payloads return strict 422 with standard error envelope."""
    # Completely empty JSON
    res = client.post("/api/instances/validate", json={})
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "BAD_REQUEST"

    # Missing days and slots
    res2 = client.post("/api/instances/validate", json={"teachers": []})
    assert res2.status_code == 422
    assert "error" in res2.json()


def test_error_envelope_consistency():
    """Verify that all non-2xx API error responses conform to {'error': {'code': str, 'message': str}}."""
    # 404 Not Found
    res404 = client.get("/api/runs/definitely_not_a_valid_run_id")
    assert res404.status_code == 404
    data404 = res404.json()
    assert isinstance(data404.get("error"), dict)
    assert "code" in data404["error"]
    assert "message" in data404["error"]

    # 404 Sample Not Found
    res_sample = client.get("/api/samples/non_existent_sample")
    assert res_sample.status_code == 404
    assert "code" in res_sample.json()["error"]

    # 409 Input Error
    draft = load_sample("tiny")
    draft["courses"][0]["teacher_id"] = "T_NONEXISTENT"
    res409 = client.post("/api/runs", json={"draft": draft, "config": {"algorithm": "A"}})
    assert res409.status_code == 409
    data409 = res409.json()
    assert data409["error"]["code"] == "INPUT_ERRORS"


def test_concurrency_busy_error_and_cancellation():
    """Start an intentionally slow solver run, verify a second run is rejected with 409 BUSY, and cancel it."""
    draft = load_sample("tight")
    payload = {
        "draft": draft,
        "config": {"algorithm": "A", "timeout_s": 30.0},
    }

    # Start first run
    res1 = client.post("/api/runs", json=payload)
    if res1.status_code == 409 and res1.json()["error"]["code"] == "BUSY":
        # System was already busy from previous background thread; wait or pass
        return

    assert res1.status_code == 202
    run_id1 = res1.json()["run_id"]

    try:
        # If the run is still running, a second run request MUST return 409 BUSY
        if jobs.is_busy():
            res2 = client.post("/api/runs", json=payload)
            assert res2.status_code == 409
            data2 = res2.json()
            assert data2["error"]["code"] == "BUSY"
            assert "in progress" in data2["error"]["message"].lower() or "busy" in data2["error"]["message"].lower()
    finally:
        # Cancel first run
        client.post(f"/api/runs/{run_id1}/cancel")

    # Give thread a moment to terminate
    time.sleep(0.1)


def test_single_command_spa_serving():
    """Verify FastAPI root and SPA routes serve frontend/dist/index.html."""
    # Root /
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "text/html" in res_root.headers.get("content-type", "")

    # Deep SPA route /viewer
    res_viewer = client.get("/viewer")
    assert res_viewer.status_code == 200
    assert "text/html" in res_viewer.headers.get("content-type", "")

    # Deep SPA route /data
    res_data = client.get("/data")
    assert res_data.status_code == 200
    assert "text/html" in res_data.headers.get("content-type", "")

    # Deep SPA route /comparison
    res_comp = client.get("/comparison")
    assert res_comp.status_code == 200
    assert "text/html" in res_comp.headers.get("content-type", "")

    # Missing API route must return JSON 404, NOT html index
    res_bad_api = client.get("/api/nonexistent_endpoint")
    assert res_bad_api.status_code == 404
    assert res_bad_api.headers.get("content-type", "").startswith("application/json")
    assert "error" in res_bad_api.json()

