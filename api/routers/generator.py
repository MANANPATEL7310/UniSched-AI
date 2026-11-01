"""FastAPI router for synthetic instance generation and preset retrieval."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter

from api.schemas import GeneratorConfigModel, InstanceDraftModel
from data.generator import PRESETS, GeneratorConfig, generate_instance
from data.loader import draft_from_instance

router = APIRouter(tags=["generator"])


@router.get("/generator/presets")
def get_presets() -> dict[str, dict[str, Any]]:
    """Return available synthetic instance generation presets."""
    return {
        name: {
            "name": cfg.name,
            "num_days": cfg.num_days,
            "slots_per_day": cfg.slots_per_day,
            "num_divisions": cfg.num_divisions,
            "num_teachers": cfg.num_teachers,
            "num_courses": cfg.num_courses,
            "num_rooms": cfg.num_rooms,
            "availability_density": cfg.availability_density,
            "tightness": cfg.tightness,
            "seed": cfg.seed,
        }
        for name, cfg in PRESETS.items()
    }


@router.post("/instances/generate", response_model=InstanceDraftModel)
def generate_draft(body: GeneratorConfigModel) -> dict[str, Any]:
    """Generate a feasible synthetic instance draft from specified generator parameters."""
    cfg = GeneratorConfig(
        name=body.name,
        num_days=body.num_days,
        slots_per_day=body.slots_per_day,
        num_divisions=body.num_divisions,
        num_teachers=body.num_teachers,
        num_courses=body.num_courses,
        num_rooms=body.num_rooms,
        availability_density=body.availability_density,
        tightness=body.tightness,
        seed=body.seed,
    )

    instance = generate_instance(cfg)
    draft = draft_from_instance(instance)
    draft["name"] = cfg.name
    return draft
