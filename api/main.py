"""FastAPI main application entrypoint with middleware, error handlers, and routers."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routers import instances, samples
from errors import (
    BusyError,
    DataLoadError,
    GenerationError,
    InputValidationError,
    NotFoundError,
    TimetableError,
)

logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="Timetable CSP API", version="1.0")

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    content: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)


# --- Error handlers ---

@app.exception_handler(DataLoadError)
async def data_load_error_handler(request: Request, exc: DataLoadError) -> JSONResponse:
    return _error_response(400, "DATA_LOAD_ERROR", str(exc))


@app.exception_handler(GenerationError)
async def generation_error_handler(request: Request, exc: GenerationError) -> JSONResponse:
    return _error_response(400, "GENERATION_ERROR", str(exc))


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(404, "NOT_FOUND", str(exc))


@app.exception_handler(BusyError)
async def busy_error_handler(request: Request, exc: BusyError) -> JSONResponse:
    return _error_response(409, "BUSY", str(exc))


@app.exception_handler(InputValidationError)
async def input_validation_error_handler(request: Request, exc: InputValidationError) -> JSONResponse:
    from api.serializers import issue_to_dto

    details = [issue_to_dto(i) for i in exc.issues]
    return _error_response(409, "INPUT_ERRORS", str(exc), details=details)


@app.exception_handler(StarletteHTTPException)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException | StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    code = "BAD_REQUEST" if exc.status_code == 400 else ("SAMPLE_NOT_FOUND" if exc.status_code == 404 else "ERROR")
    return _error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = ".".join(str(x) for x in first_err.get("loc", []))
    msg = first_err.get("msg", "Validation error")
    formatted_msg = f"{loc}: {msg}" if loc else msg
    return _error_response(422, "BAD_REQUEST", formatted_msg, details=errors)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected server error: %s", exc)
    return _error_response(500, "INTERNAL", "Unexpected server error")


# --- Health endpoints ---

@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0"}


# --- Include Routers ---
app.include_router(samples.router, prefix="/api")
app.include_router(instances.router, prefix="/api")

# --- Optional static mount for frontend production build ---
dist_path = Path("frontend/dist")
if dist_path.exists():
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
