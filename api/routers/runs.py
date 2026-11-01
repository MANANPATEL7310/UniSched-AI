"""Router for search run endpoints (/api/runs)."""
from __future__ import annotations

from dataclasses import replace
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from api.jobs import jobs
from api.schemas import RunRequest, RunResponseModel
from api.serializers import outcome_to_dto, progress_to_dto
from csp.result import PRESETS
from data.loader import instance_from_draft
from data.validator import validate_instance
from errors import InputValidationError

router = APIRouter(tags=["runs"])


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run_endpoint(req: RunRequest) -> dict[str, str]:
    """Validate instance draft and launch background CSP solver run."""
    # Convert Pydantic draft to dict
    draft_dict = req.draft.model_dump()
    instance = instance_from_draft(draft_dict)

    # Validate instance; abort with 409 if any ERROR issues exist
    issues = validate_instance(instance)
    errors = [x for x in issues if x.severity == "ERROR"]
    if errors:
        raise InputValidationError(errors)

    # Configure search parameters based on algorithm preset and requested limits
    base_cfg = PRESETS[req.config.algorithm]
    search_cfg = replace(
        base_cfg,
        timeout_s=req.config.timeout_s,
        node_limit=req.config.node_limit,
    )

    run_id = jobs.start_run(instance, search_cfg, req.config.algorithm)
    return {"run_id": run_id}


@router.get("/runs/{run_id}", response_model=RunResponseModel)
def get_run_endpoint(run_id: str) -> dict[str, Any]:
    """Poll progress and outcome of a background run."""
    record = jobs.get_run(run_id)
    handle = record.handle
    progress_dto = progress_to_dto(handle.progress())

    if not handle.is_done():
        return {
            "run_id": run_id,
            "state": "running",
            "progress": progress_dto,
            "outcome": None,
            "error": None,
        }

    err = handle.error()
    if err is not None:
        return {
            "run_id": run_id,
            "state": "error",
            "progress": progress_dto,
            "outcome": None,
            "error": {"code": "INTERNAL", "message": str(err)},
        }

    # Finished successfully
    if record.cached_outcome_dto is None:
        outcome_obj = handle.outcome()
        if outcome_obj is not None:
            record.cached_outcome_dto = outcome_to_dto(
                outcome_obj, run_id, record.algorithm
            )

    return {
        "run_id": run_id,
        "state": "done",
        "progress": progress_dto,
        "outcome": record.cached_outcome_dto,
        "error": None,
    }


@router.post("/runs/{run_id}/cancel")
def cancel_run_endpoint(run_id: str) -> dict[str, bool]:
    """Request cancellation of an active run (idempotent)."""
    jobs.cancel_run(run_id)
    return {"ok": True}


@router.get("/runs/{run_id}/timetable.csv")
def download_timetable_csv(run_id: str) -> Response:
    """Download the completed timetable for a run as a UTF-8 CSV attachment."""
    record = jobs.get_run(run_id)
    handle = record.handle

    if not handle.is_done():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "NO_TIMETABLE", "message": "Search run is still in progress."}},
        )

    outcome = handle.outcome()
    if outcome is None or outcome.timetable is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "NO_TIMETABLE", "message": "No timetable was produced for this run."}},
        )

    csv_bytes = outcome.timetable.to_csv_bytes()
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", record.instance_name)
    filename = f"{safe_name}_timetable.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
