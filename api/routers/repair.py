"""HTTP endpoints for timetable repair, minimal-change rescheduling, and soft constraint optimization."""
from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, HTTPException

from api.schemas import (
    RepairRequestModel,
    RepairResponseModel,
    SoftImproveRequestModel,
    SoftImproveResponseModel,
)
from api.serializers import diff_to_dto, metrics_to_dto, soft_to_dto, timetable_to_dto, validation_to_dto
from csp.result import SearchMetrics
from data.loader import instance_from_draft
from models.timetable import Timetable
from scheduling.rescheduler import (
    RoomUnavailableChange,
    TeacherUnavailableChange,
    reschedule,
)
from scheduling.soft_constraints import soft_penalty
from scheduling.soft_improvement import improve_soft_constraints

router = APIRouter(tags=["repair"])


@router.post("/repair", response_model=RepairResponseModel)
def repair_timetable(req: RepairRequestModel) -> dict[str, Any]:
    """Perform minimal-change rescheduling on a published timetable given an unavailability change."""
    try:
        instance = instance_from_draft(req.draft.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid instance draft: {e}")

    try:
        published_tt = Timetable.from_json_dict(instance, req.published.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid published timetable: {e}")

    # Build typed change
    if req.change.type == "teacher_unavailable":
        change = TeacherUnavailableChange(
            teacher_id=req.change.entity_id,
            day=req.change.day,
            slot=req.change.slot,
        )
    elif req.change.type == "room_unavailable":
        change = RoomUnavailableChange(
            room_id=req.change.entity_id,
            day=req.change.day,
            slot=req.change.slot,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported change type '{req.change.type}'")

    res = reschedule(
        instance_old=instance,
        timetable_old=published_tt,
        change=change,
        locks_policy=req.lock_policy,
        timeout_s=req.timeout_s,
    )

    outcome_dto: dict[str, Any] | None = None
    if res.status == "SOLVED" and res.timetable is not None:
        soft_rep = soft_penalty(res.timetable.instance, res.timetable.assignment)
        outcome_dto = {
            "run_id": f"repair_{uuid.uuid4().hex[:8]}",
            "algorithm": "D",
            "status": res.status,
            "message": res.message,
            "is_valid": res.validation.is_valid if res.validation else False,
            "num_sessions": len(res.timetable.instance.sessions),
            "metrics": metrics_to_dto(res.metrics, runtime_s=res.metrics.runtime_s),
            "timetable": timetable_to_dto(res.timetable),
            "validation": validation_to_dto(res.validation),
            "soft": soft_to_dto(soft_rep),
        }

    return {
        "status": res.status,
        "outcome": outcome_dto,
        "diff": [diff_to_dto(d) for d in res.diff],
        "relaxed_locks": res.relaxed_locks,
        "change_penalty": res.change_penalty,
        "message": res.message,
    }


@router.post("/repair/improve-soft", response_model=SoftImproveResponseModel)
def improve_soft(req: SoftImproveRequestModel) -> dict[str, Any]:
    """Optimize soft constraints on a valid published timetable using hill-climbing local search."""
    try:
        instance = instance_from_draft(req.draft.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid instance draft: {e}")

    try:
        published_tt = Timetable.from_json_dict(instance, req.published.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid published timetable: {e}")

    try:
        res = improve_soft_constraints(
            instance=instance,
            timetable=published_tt,
            max_steps=req.max_steps,
            time_limit_s=req.time_limit_s,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    outcome_dto = {
        "run_id": f"improve_{uuid.uuid4().hex[:8]}",
        "algorithm": "LocalSearch",
        "status": "SOLVED",
        "message": res.message,
        "is_valid": res.validation.is_valid,
        "num_sessions": len(res.timetable.instance.sessions),
        "metrics": metrics_to_dto(SearchMetrics()),
        "timetable": timetable_to_dto(res.timetable),
        "validation": validation_to_dto(res.validation),
        "soft": soft_to_dto(res.report),
    }

    return {
        "status": res.status,
        "initial_penalty": res.initial_penalty,
        "improved_penalty": res.improved_penalty,
        "steps_accepted": res.steps_accepted,
        "outcome": outcome_dto,
        "message": res.message,
    }

