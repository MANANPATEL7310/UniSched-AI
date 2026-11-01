"""FastAPI router for sample dataset operations."""
from __future__ import annotations

import re
from fastapi import APIRouter, HTTPException

from data.loader import list_samples, load_sample
from errors import DataLoadError

router = APIRouter(tags=["samples"])

_VALID_SAMPLE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


@router.get("/samples")
def get_samples() -> list[dict[str, str]]:
    """List all bundled sample datasets."""
    return [{"name": s.name, "description": s.description} for s in list_samples()]


@router.get("/samples/{name}")
def get_sample_draft(name: str) -> dict:
    """Retrieve an editable draft dictionary for a named sample dataset."""
    if not _VALID_SAMPLE_NAME.match(name):
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SAMPLE_NOT_FOUND", "message": f"Sample '{name}' not found."}},
        )

    try:
        return load_sample(name)
    except DataLoadError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SAMPLE_NOT_FOUND", "message": str(e)}},
        )
