"""JobManager handling background solve runs and benchmark execution."""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
from time import time
from typing import Any
import uuid

from errors import BusyError, NotFoundError
from scheduling.scheduler import RunHandle, start_run


@dataclass
class RunRecord:
    """Tracking record for a single timetable search run."""

    run_id: str
    handle: RunHandle
    algorithm: str
    instance_name: str
    created_at: float = field(default_factory=time)
    cached_outcome_dto: dict[str, Any] | None = None


@dataclass
class BenchRecord:
    """Tracking record for a benchmark job (Stage 5)."""

    job_id: str
    state: str  # "running" | "done" | "error"
    created_at: float = field(default_factory=time)
    done: int = 0
    total: int = 0
    rows: list[dict[str, Any]] | None = None
    meta: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


class JobManager:
    """Manages active and historical runs/benchmarks with concurrency limits and cleanup."""

    def __init__(self, max_records: int = 30, ttl_s: int = 7200) -> None:
        self.max_records = max_records
        self.ttl_s = ttl_s
        self._lock = threading.RLock()
        self._runs: dict[str, RunRecord] = {}
        self._benchmarks: dict[str, BenchRecord] = {}

    def is_busy(self) -> bool:
        """Check if any run or benchmark is currently actively computing."""
        with self._lock:
            return self._is_busy_locked()

    def _is_busy_locked(self) -> bool:
        """Check busy state assuming _lock is already held."""
        for record in self._runs.values():
            if not record.handle.is_done():
                return True
        for bench in self._benchmarks.values():
            if bench.state == "running":
                return True
        return False

    def _cleanup_old_records_locked(self) -> None:
        """Prune expired or excess finished records (must be called with _lock held)."""
        now = time()
        # Clean runs older than TTL
        expired_runs = [
            rid
            for rid, rec in self._runs.items()
            if rec.handle.is_done() and (now - rec.created_at) > self.ttl_s
        ]
        for rid in expired_runs:
            del self._runs[rid]

        # If still over max_records, remove oldest finished runs
        finished_runs = [
            (rec.created_at, rid)
            for rid, rec in self._runs.items()
            if rec.handle.is_done()
        ]
        finished_runs.sort()
        while len(self._runs) > self.max_records and finished_runs:
            _, rid = finished_runs.pop(0)
            self._runs.pop(rid, None)

    def start_run(self, instance: Any, config: Any, algorithm: str) -> str:
        """Start a background run for the given instance and config, returning run_id."""
        with self._lock:
            if self._is_busy_locked():
                raise BusyError("Another run or benchmark is already in progress.")

            self._cleanup_old_records_locked()
            run_id = uuid.uuid4().hex[:12]
            handle = start_run(instance, config)
            self._runs[run_id] = RunRecord(
                run_id=run_id,
                handle=handle,
                algorithm=algorithm,
                instance_name=instance.name,
            )
            return run_id

    def get_run(self, run_id: str) -> RunRecord:
        """Retrieve a RunRecord by ID or raise NotFoundError."""
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                raise NotFoundError(f"Run '{run_id}' not found.")
            return record

    def cancel_run(self, run_id: str) -> None:
        """Cancel an ongoing run. Idempotent if already finished."""
        with self._lock:
            record = self._runs.get(run_id)
            if record is not None:
                record.handle.cancel()

    def cancel_all(self) -> None:
        """Signal cancellation to all active runs and benchmarks (e.g. on server shutdown)."""
        with self._lock:
            for rec in self._runs.values():
                rec.handle.cancel()
            for b in self._benchmarks.values():
                b.cancel_event.set()


# Singleton instance
jobs = JobManager()
