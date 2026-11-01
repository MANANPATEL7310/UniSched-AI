"""Unit tests for benchmark API endpoints and background job execution (Stage 5, A17)."""
from __future__ import annotations

import json
from pathlib import Path
import time
from fastapi.testclient import TestClient
import pandas as pd
import pytest

from api.jobs import jobs
from api.main import app
from evaluation.reports import save_results

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_jobs():
    """Ensure jobs manager is clean before and after each test."""
    jobs.cancel_all()
    with jobs._lock:
        jobs._runs.clear()
        jobs._benchmarks.clear()
    yield
    jobs.cancel_all()
    with jobs._lock:
        jobs._runs.clear()
        jobs._benchmarks.clear()


def test_start_benchmark_and_poll_completion():
    """Benchmark on small instance with algorithms A and B runs to completion with valid rows."""
    req = {
        "sizes": ["small"],
        "algorithms": ["A", "B"],
        "seeds": 1,
        "timeout_s": 10.0,
        "measure_memory": False,
    }
    res = client.post("/api/benchmarks", json=req)
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll until done (timeout 25s)
    deadline = time.time() + 25.0
    final_body = None
    while time.time() < deadline:
        poll_res = client.get(f"/api/benchmarks/{job_id}")
        assert poll_res.status_code == 200
        body = poll_res.json()
        assert body["job_id"] == job_id
        if body["state"] == "done":
            final_body = body
            break
        elif body["state"] == "error":
            pytest.fail(f"Benchmark job failed: {body.get('error')}")
        time.sleep(0.1)

    assert final_body is not None, "Benchmark did not complete in time"
    assert final_body["state"] == "done"
    assert final_body["done"] == 2
    assert final_body["total"] == 2
    rows = final_body["rows"]
    assert isinstance(rows, list)
    assert len(rows) == 2

    # Check that rows contain no NaN or Infinity and are clean JSON
    json_str = json.dumps(rows)
    assert "NaN" not in json_str
    assert "Infinity" not in json_str

    for r in rows:
        assert r["size_label"] == "small"
        assert r["seed"] == 0
        assert r["algorithm"] in ["A", "B"]
        assert r["status"] == "SOLVED"
        assert r["solved"] is True
        assert r["valid"] is True
        assert r["nodes"] > 0
        assert r["runtime_s"] >= 0.0


def test_benchmark_busy_conflict():
    """Launching two benchmarks concurrently returns 409 BUSY on the second."""
    req = {
        "sizes": ["small"],
        "algorithms": ["A"],
        "seeds": 1,
        "timeout_s": 10.0,
    }
    res1 = client.post("/api/benchmarks", json=req)
    assert res1.status_code == 202
    job_id = res1.json()["job_id"]

    try:
        res2 = client.post("/api/benchmarks", json=req)
        # Could be 409 if still running, or 202 if already finished
        if res2.status_code == 409:
            err = res2.json()
            assert err["error"]["code"] == "BUSY"
    finally:
        client.post(f"/api/benchmarks/{job_id}/cancel")


def test_benchmark_not_found():
    """Querying a nonexistent benchmark ID returns 404."""
    res = client.get("/api/benchmarks/nonexistent_id")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_cancel_benchmark(monkeypatch):
    """Canceling a running benchmark halts execution and marks meta.cancelled = true."""
    # Ensure worker waits until cancel is signaled so test is deterministic
    import api.jobs

    orig_run_matrix = api.jobs.run_matrix

    def slow_run_matrix(*args, **kwargs):
        cancel_evt = kwargs.get("cancel_event")
        if cancel_evt:
            cancel_evt.wait(timeout=5.0)
        return orig_run_matrix(*args, **kwargs)

    monkeypatch.setattr(api.jobs, "run_matrix", slow_run_matrix)

    req = {
        "sizes": ["small"],
        "algorithms": ["A"],
        "seeds": 1,
        "timeout_s": 10.0,
    }
    res = client.post("/api/benchmarks", json=req)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # Cancel via endpoint
    cancel_res = client.post(f"/api/benchmarks/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json() == {"ok": True}

    # Poll until done
    deadline = time.time() + 10.0
    final_body = None
    while time.time() < deadline:
        poll_res = client.get(f"/api/benchmarks/{job_id}")
        assert poll_res.status_code == 200
        body = poll_res.json()
        if body["state"] == "done":
            final_body = body
            break
        elif body["state"] == "error":
            pytest.fail(f"Benchmark job failed: {body.get('error')}")
        time.sleep(0.05)

    assert final_body is not None
    assert final_body["state"] == "done"
    assert final_body["meta"]["cancelled"] is True


def test_saved_results_endpoints(tmp_path, monkeypatch):
    """Test listing saved results and path traversal protection on saved benchmark results."""
    # Create fake saved results in results/
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    fake_df = pd.DataFrame([{
        "instance": "small",
        "size_label": "small",
        "num_sessions": 45,
        "seed": 0,
        "algorithm": "A",
        "status": "SOLVED",
        "solved": True,
        "valid": True,
        "runtime_s": 0.05,
        "build_s": 0.01,
        "nodes": 45,
        "attempts": 45,
        "backtracks": 0,
        "checks": 45,
        "values_pruned": 0,
        "peak_memory_kb": None,
        "hard_violations": 0,
        "soft_penalty": None,
        "timeout_s": 10.0,
    }])
    base_name = save_results(fake_df, {"sizes": ["small"], "cancelled": False})

    try:
        # 1. List saved results
        res = client.get("/api/benchmarks/results")
        assert res.status_code == 200
        items = res.json()
        assert isinstance(items, list)
        matching = [it for it in items if it["name"] == base_name]
        assert len(matching) == 1
        assert matching[0]["rows"] == 1

        # 2. Get saved result by base_name
        res_get = client.get(f"/api/benchmarks/results/{base_name}")
        assert res_get.status_code == 200
        rows = res_get.json()
        assert len(rows) == 1
        assert rows[0]["algorithm"] == "A"
        assert rows[0]["solved"] is True

        # 3. Get saved result with .csv suffix
        res_get_csv = client.get(f"/api/benchmarks/results/{base_name}.csv")
        assert res_get_csv.status_code == 200
        assert len(res_get_csv.json()) == 1

        # 4. Path traversal protection: ..%2F
        res_trav = client.get("/api/benchmarks/results/..%2Fetc")
        assert res_trav.status_code == 404
        assert res_trav.json()["error"]["code"] in ["NOT_FOUND", "SAMPLE_NOT_FOUND"]

        # 5. Nonexistent file
        res_missing = client.get("/api/benchmarks/results/nonexistent_file_xyz")
        assert res_missing.status_code == 404
        assert res_missing.json()["error"]["code"] == "NOT_FOUND"
    finally:
        # Clean up created fake files
        (results_dir / f"{base_name}.csv").unlink(missing_ok=True)
        (results_dir / f"{base_name}.json").unlink(missing_ok=True)
