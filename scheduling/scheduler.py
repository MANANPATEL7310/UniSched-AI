"""Scheduler facade and background run controller."""
from __future__ import annotations

from dataclasses import dataclass
import threading
from time import perf_counter
from typing import TYPE_CHECKING, Any

from csp.backtracking import solve
from csp.problem import build_csp
from csp.result import (
    PRESETS,
    ProgressState,
    RunControl,
    SearchConfig,
    SearchMetrics,
    SearchResult,
    SearchStatus,
)
from data.validator import validate_instance
from errors import InputValidationError
from models.timetable import Timetable
from scheduling.timetable_validator import ValidationReport, validate_timetable

# Optional soft constraints import (Stage 3 B12)
try:
    from scheduling.soft_constraints import SoftReport, soft_penalty  # type: ignore
except ImportError:
    SoftReport = None  # type: ignore
    soft_penalty = None

if TYPE_CHECKING:
    from models.instance import SchedulingInstance


@dataclass
class ScheduleOutcome:
    """Comprehensive outcome of a timetable generation run."""

    result: SearchResult
    timetable: Timetable | None
    validation: ValidationReport | None
    soft: Any | None
    is_valid: bool
    build_s: float
    num_sessions: int

    @property
    def status(self) -> SearchStatus:
        """Search termination status."""
        return self.result.status

    @property
    def message(self) -> str:
        """Human-readable explanation of the search outcome."""
        return self.result.message

    @property
    def metrics(self) -> SearchMetrics:
        """Search execution metrics."""
        return self.result.metrics

    @property
    def runtime_s(self) -> float:
        """Search execution runtime in seconds."""
        return self.result.metrics.runtime_s

    @property
    def peak_memory_kb(self) -> int | None:
        """Peak memory usage in KB if measured, else None."""
        return self.result.metrics.peak_memory_kb


def generate_timetable(
    instance: SchedulingInstance,
    config: SearchConfig | None = None,
    control: RunControl | None = None,
) -> ScheduleOutcome:
    """Generate a validated timetable for an instance or report failure.

    Steps:
    1. Validate instance with data.validator.validate_instance.
       If any ERROR severity issues exist, raise InputValidationError.
    2. Build CSPProblem and record build duration build_s.
    3. Run search with solve().
    4. If SOLVED:
       - Construct Timetable object.
       - Run independent validate_timetable().
       - Compute soft penalty if valid and soft_penalty module available.
       - is_valid is True iff SOLVED and validate_timetable reports is_valid True.
    5. Return ScheduleOutcome.
    """
    issues = validate_instance(instance)
    errors = [x for x in issues if x.severity == "ERROR"]
    if errors:
        raise InputValidationError(errors)

    t0 = perf_counter()
    problem = build_csp(instance)
    build_s = perf_counter() - t0

    cfg = config or PRESETS["A"]
    result = solve(problem, cfg, control=control)
    result.metrics.build_s = build_s
    n = len(instance.sessions)

    if result.status is SearchStatus.SOLVED and result.assignment is not None:
        tt = Timetable(instance, result.assignment)
        report = validate_timetable(instance, result.assignment)
        soft = None
        if report.is_valid and soft_penalty is not None:
            soft = soft_penalty(instance, result.assignment)

        return ScheduleOutcome(
            result=result,
            timetable=tt,
            validation=report,
            soft=soft,
            is_valid=report.is_valid,
            build_s=build_s,
            num_sessions=n,
        )

    return ScheduleOutcome(
        result=result,
        timetable=None,
        validation=None,
        soft=None,
        is_valid=False,
        build_s=build_s,
        num_sessions=n,
    )


class RunHandle:
    """Controls and monitors a background timetable generation thread."""

    def __init__(
        self,
        instance: SchedulingInstance,
        config: SearchConfig | None = None,
    ) -> None:
        self._cancel_event = threading.Event()
        self._progress = ProgressState(total=len(instance.sessions))
        self._control = RunControl(
            cancel_event=self._cancel_event, progress=self._progress
        )
        self._outcome: ScheduleOutcome | None = None
        self._error: Exception | None = None
        self._done = threading.Event()

        self._thread = threading.Thread(
            target=self._run,
            args=(instance, config),
            daemon=True,
            name=f"RunHandle-{instance.name}",
        )
        self._thread.start()

    def _run(
        self, instance: SchedulingInstance, config: SearchConfig | None
    ) -> None:
        try:
            self._outcome = generate_timetable(
                instance, config, control=self._control
            )
        except Exception as exc:
            self._error = exc
        finally:
            self._done.set()

    def progress(self) -> ProgressState:
        """Return the current thread-safe progress snapshot."""
        return self._progress

    def is_done(self) -> bool:
        """Return True if the background generation thread has finished."""
        return self._done.is_set()

    def cancel(self) -> None:
        """Signal the solver thread to abort at the next search step."""
        self._cancel_event.set()

    def outcome(self) -> ScheduleOutcome | None:
        """Return the finished ScheduleOutcome, or None if still running or errored."""
        return self._outcome

    def error(self) -> Exception | None:
        """Return any unhandled Exception raised by the worker thread, or None."""
        return self._error

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for worker thread completion. Returns True if finished, False on timeout."""
        return self._done.wait(timeout=timeout)


def start_run(
    instance: SchedulingInstance,
    config: SearchConfig | None = None,
) -> RunHandle:
    """Start an asynchronous timetable generation job in a daemon background thread."""
    return RunHandle(instance, config)
