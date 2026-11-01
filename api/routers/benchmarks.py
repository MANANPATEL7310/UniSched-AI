"""FastAPI router for benchmark jobs and saved results."""
from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import re
from typing import Any

from fastapi import APIRouter, HTTPException, status
import pandas as pd

from api.jobs import jobs
from api.schemas import (
    BenchmarkRequestModel,
    BenchmarkResponseModel,
    SavedResultInfoModel,
)
from evaluation.reports import load_results

router = APIRouter(tags=["benchmarks"])

_VALID_RESULT_NAME = re.compile(r"^[A-Za-z0-9_-]+(?:\.csv)?$")


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


@router.post("/benchmarks", status_code=status.HTTP_202_ACCEPTED)
def start_benchmark_endpoint(req: BenchmarkRequestModel) -> dict[str, str]:
    """Launch a background benchmark suite for selected sizes and algorithms."""
    job_id = jobs.start_benchmark(req)
    return {"job_id": job_id}


@router.get("/benchmarks/results", response_model=list[SavedResultInfoModel])
def list_saved_results_endpoint() -> list[dict[str, Any]]:
    """List historical benchmark runs stored in the results directory."""
    results_dir = Path("results")
    if not results_dir.exists():
        return []

    items = []
    for csv_path in results_dir.glob("*.csv"):
        name = csv_path.stem
        try:
            mtime = csv_path.stat().st_mtime
            created_str = datetime.fromtimestamp(mtime).isoformat()
            lines = [line for line in csv_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            num_rows = max(0, len(lines) - 1)
            items.append({
                "name": name,
                "created": created_str,
                "rows": num_rows,
                "mtime": mtime,
            })
        except Exception:
            continue

    # Sort newest first
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return [{"name": it["name"], "created": it["created"], "rows": it["rows"]} for it in items]


@router.get("/benchmarks/results/{name}")
def get_saved_result_endpoint(name: str) -> list[dict[str, Any]]:
    """Retrieve raw benchmark rows from a saved result CSV file."""
    if not _VALID_RESULT_NAME.match(name) or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Benchmark result '{name}' not found."}},
        )

    base_name = name[:-4] if name.endswith(".csv") else name
    results_dir = Path("results")
    csv_file = (results_dir / f"{base_name}.csv").resolve()

    try:
        csv_file.relative_to(results_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Benchmark result '{name}' not found."}},
        )

    if not csv_file.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Benchmark result '{name}' not found."}},
        )

    try:
        df = load_results(str(csv_file))
        raw_rows = df.to_dict(orient="records")
        return [_clean_row(r) for r in raw_rows]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL", "message": str(exc)}},
        )


@router.get("/benchmarks/{job_id}", response_model=BenchmarkResponseModel)
def get_benchmark_endpoint(job_id: str) -> dict[str, Any]:
    """Poll benchmark execution status, progress, and results."""
    record = jobs.get_benchmark(job_id)
    return {
        "job_id": record.job_id,
        "state": record.state,
        "done": record.done,
        "total": record.total,
        "rows": record.rows,
        "meta": record.meta,
        "error": record.error,
    }


@router.post("/benchmarks/{job_id}/cancel")
def cancel_benchmark_endpoint(job_id: str) -> dict[str, bool]:
    """Request early cancellation of an active benchmark job (idempotent)."""
    jobs.cancel_benchmark(job_id)
    return {"ok": True}
