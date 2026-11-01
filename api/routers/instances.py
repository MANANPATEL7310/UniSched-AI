"""FastAPI router for instance draft validation and CSV uploads."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas import InstanceDraftModel, ValidateResponseModel
from api.serializers import issue_to_dto
from data.loader import draft_from_csv_files, instance_from_draft
from data.validator import validate_instance
from errors import DataLoadError

router = APIRouter(tags=["instances"])

MAX_UPLOAD_FILES = 10
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB per file


@router.post("/instances/upload-csv")
def upload_csv(files: list[UploadFile] = File(...)) -> dict:
    """Parse a collection of 1-10 uploaded CSV files into an editable draft."""
    if not files:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "DATA_LOAD_ERROR", "message": "No files uploaded."}},
        )
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=413,
            detail={"error": {"code": "TOO_LARGE", "message": f"Too many files: maximum is {MAX_UPLOAD_FILES}."}},
        )

    file_contents: dict[str, bytes] = {}
    for f in files:
        filename = f.filename or ""
        content = f.file.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={"error": {"code": "TOO_LARGE", "message": f"File '{filename}' exceeds 2 MB limit."}},
            )
        file_contents[filename] = content

    return draft_from_csv_files(file_contents)


@router.post("/instances/validate", response_model=ValidateResponseModel)
def validate_draft(draft: InstanceDraftModel) -> dict:
    """Validate an instance draft before search starts.
    
    Always returns HTTP 200 with parse_error or issues list and summary metrics.
    """
    raw_dict = draft.model_dump()
    try:
        instance = instance_from_draft(raw_dict)
    except DataLoadError as e:
        return {
            "parse_error": str(e),
            "issues": [],
            "summary": None,
        }

    issues = validate_instance(instance)
    summary = {
        "courses": len(instance.courses),
        "teachers": len(instance.teachers),
        "rooms": len(instance.rooms),
        "divisions": len(instance.divisions),
        "sessions": len(instance.sessions),
    }

    return {
        "parse_error": None,
        "issues": [issue_to_dto(i) for i in issues],
        "summary": summary,
    }
