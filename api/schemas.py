"""Pydantic request and response schemas mirroring frontend/src/api/types.ts."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- Base Draft Models ---

class SlotDefModel(_M):
    start: str
    end: str


class TeacherModel(_M):
    teacher_id: str
    teacher_name: str = ""
    unavailable_slots: list[str] = Field(default_factory=list)
    preferred_slots: list[str] = Field(default_factory=list)
    max_daily_sessions: int | None = None


class CourseModel(_M):
    course_id: str
    course_name: str = ""
    teacher_id: str
    sessions_per_week: int
    duration_slots: int
    room_types: list[str]
    eligible_divisions: list[str]


class DivisionModel(_M):
    division_id: str
    division_name: str = ""
    student_count: int
    enrolled_courses: list[str]


class RoomModel(_M):
    room_id: str
    room_name: str = ""
    room_type: str
    capacity: int
    unavailable_slots: list[str] = Field(default_factory=list)


class FixedModel(_M):
    session_id: str
    day_name: str
    start_time: str
    room_id: str


class InstanceDraftModel(_M):
    name: str = "Untitled"
    days: list[str] = Field(max_length=14)
    slots: list[SlotDefModel] = Field(max_length=48)
    teachers: list[TeacherModel] = Field(max_length=300)
    courses: list[CourseModel] = Field(max_length=500)
    divisions: list[DivisionModel] = Field(max_length=300)
    rooms: list[RoomModel] = Field(max_length=300)
    fixed_assignments: list[FixedModel] = Field(default_factory=list, max_length=2000)


# --- Request Models ---

class RunConfigModel(_M):
    algorithm: Literal["A", "B", "C", "D"]
    timeout_s: float = Field(60.0, ge=1, le=3600)
    node_limit: int | None = Field(None, ge=1)


class RunRequest(_M):
    draft: InstanceDraftModel
    config: RunConfigModel


class GeneratorConfigModel(_M):
    name: str = "generated"
    num_days: int = Field(5, ge=1, le=7)
    slots_per_day: int = Field(6, ge=1, le=12)
    num_divisions: int = Field(3, ge=1, le=30)
    num_teachers: int = Field(4, ge=1, le=60)
    num_courses: int = Field(6, ge=1, le=80)
    num_rooms: int = Field(4, ge=1, le=40)
    availability_density: float = Field(0.3, ge=0.0, le=1.0)
    tightness: float = Field(0.5, ge=0.0, le=1.0)
    seed: int = 0


class BenchmarkRequestModel(_M):
    sizes: list[Literal["small", "medium", "large"]] = Field(min_length=1)
    algorithms: list[Literal["A", "B", "C", "D"]] = Field(min_length=1)
    seeds: int = Field(1, ge=1, le=5)
    timeout_s: float = Field(30.0, ge=1, le=600)
    measure_memory: bool = False


# --- Response Models ---

class InputIssueModel(_M):
    severity: Literal["ERROR", "WARNING"]
    code: str
    message: str
    entity: str | None = None


class InstanceSummaryModel(_M):
    courses: int
    teachers: int
    rooms: int
    divisions: int
    sessions: int


class ValidateResponseModel(_M):
    parse_error: str | None = None
    issues: list[InputIssueModel] = Field(default_factory=list)
    summary: InstanceSummaryModel | None = None


class SampleInfoModel(_M):
    name: str
    description: str


class ApiErrorDetail(_M):
    code: str
    message: str
    details: Any = None


class ApiErrorResponse(_M):
    error: ApiErrorDetail


class EntryModel(_M):
    session_id: str
    course_id: str
    course_name: str
    teacher_id: str
    teacher_name: str
    division_id: str
    division_name: str
    room_id: str
    room_name: str
    day: int
    day_name: str
    start_slot: int
    end_slot: int
    start_time: str
    end_time: str
    duration_slots: int


class GridDtoModel(_M):
    day_names: list[str]
    slot_starts: list[str]
    slot_ends: list[str]


class TimetableDtoModel(_M):
    grid: GridDtoModel
    entries: list[EntryModel]


class ViolationModel(_M):
    type: str
    session_ids: list[str]
    resource: str | None = None
    day: int | None = None
    slot: int | None = None
    explanation: str


class ValidationDtoModel(_M):
    is_valid: bool
    sessions_required: int
    sessions_assigned: int
    counts_by_type: dict[str, int]
    violations: list[ViolationModel]


class SoftDtoModel(_M):
    student_gap: float
    teacher_gap: float
    workload: float
    preference: float
    change: float
    total: float


class MetricsModel(_M):
    nodes: int
    attempts: int
    backtracks: int
    checks: int
    values_pruned: int
    root_pruned: int
    domain_wipeouts: int
    runtime_s: float
    build_s: float
    peak_memory_kb: float | None = None


class RunOutcomeModel(_M):
    run_id: str
    algorithm: str
    status: str
    message: str
    is_valid: bool
    num_sessions: int
    metrics: MetricsModel
    timetable: TimetableDtoModel | None = None
    validation: ValidationDtoModel | None = None
    soft: SoftDtoModel | None = None


class ProgressModel(_M):
    total: int
    assigned: int
    nodes: int
    attempts: int
    backtracks: int
    elapsed_s: float


class RunResponseModel(_M):
    run_id: str
    state: Literal["running", "done", "error"]
    progress: ProgressModel
    outcome: RunOutcomeModel | None = None
    error: ApiErrorDetail | None = None


class BenchmarkRowModel(_M):
    instance: str
    size_label: str
    num_sessions: int
    seed: int
    algorithm: Literal["A", "B", "C", "D"]
    status: str
    solved: bool
    valid: bool
    runtime_s: float
    build_s: float
    nodes: int
    attempts: int
    backtracks: int
    checks: int
    values_pruned: int
    domain_wipeouts: int | None = None
    root_pruned: int | None = None
    peak_memory_kb: float | None = None
    hard_violations: int
    soft_penalty: float | None = None
    timeout_s: float | None = None


class BenchmarkResponseModel(_M):
    job_id: str
    state: Literal["running", "done", "error"]
    done: int
    total: int
    rows: list[BenchmarkRowModel] | None = None
    meta: dict[str, Any] | None = None
    error: ApiErrorDetail | None = None


class SavedResultInfoModel(_M):
    name: str
    created: str
    rows: int

