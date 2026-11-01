"""JobManager handling background solve runs and benchmark execution."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
import threading
from time import time
from typing import Any
import uuid

import pandas as pd

from csp.result import PRESETS as SEARCH_PRESETS
from data.generator import PRESETS as GENERATOR_PRESETS, generate_instance
from errors import BusyError, NotFoundError
from evaluation.benchmarks import run_matrix
from evaluation.reports import save_results
from scheduling.scheduler import RunHandle, start_run


def _clean_metric_val(val: Any) -> Any:
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if pd.isna(val):
        return None
    return val


def _clean_row_dict(row: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


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

        # Clean benchmarks older than TTL
        expired_benchmarks = [
            bid
            for bid, b in self._benchmarks.items()
            if b.state != "running" and (now - b.created_at) > self.ttl_s
        ]
        for bid in expired_benchmarks:
            del self._benchmarks[bid]

        # If still over max_records, remove oldest finished benchmarks
        finished_benchmarks = [
            (b.created_at, bid)
            for bid, b in self._benchmarks.items()
            if b.state != "running"
        ]
        finished_benchmarks.sort()
        while len(self._benchmarks) > self.max_records and finished_benchmarks:
            _, bid = finished_benchmarks.pop(0)
            self._benchmarks.pop(bid, None)

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

    def start_benchmark(self, req: Any) -> str:
        """Start a background benchmark suite for selected sizes and algorithms."""
        with self._lock:
            if self._is_busy_locked():
                raise BusyError("Another run or benchmark is already in progress.")

            self._cleanup_old_records_locked()
            job_id = uuid.uuid4().hex[:12]
            total = len(req.sizes) * req.seeds * len(req.algorithms)
            cancel_event = threading.Event()
            bench_record = BenchRecord(
                job_id=job_id,
                state="running",
                done=0,
                total=total,
                cancel_event=cancel_event,
            )
            self._benchmarks[job_id] = bench_record

            thread = threading.Thread(
                target=self._run_benchmark_worker,
                args=(bench_record, req),
                daemon=True,
            )
            thread.start()
            return job_id

    def _run_benchmark_worker(self, record: BenchRecord, req: Any) -> None:
        try:
            instances = []
            for size in req.sizes:
                base_gen_cfg = GENERATOR_PRESETS[size]
                for s in range(req.seeds):
                    gen_cfg = replace(base_gen_cfg, seed=s)
                    inst = generate_instance(gen_cfg)
                    instances.append(inst)

            configs = []
            for algo in req.algorithms:
                base_search_cfg = SEARCH_PRESETS[algo]
                search_cfg = replace(
                    base_search_cfg,
                    timeout_s=req.timeout_s,
                    node_limit=None,
                )
                configs.append(search_cfg)

            def on_progress(done_count: int, total_count: int) -> None:
                with self._lock:
                    record.done = done_count
                    record.total = total_count

            df = run_matrix(
                instances=instances,
                configs=configs,
                trials=1,
                on_progress=on_progress,
                measure_memory=req.measure_memory,
                cancel_event=record.cancel_event,
            )

            was_cancelled = record.cancel_event.is_set()
            meta: dict[str, Any] = {
                "sizes": list(req.sizes),
                "algorithms": list(req.algorithms),
                "seeds": req.seeds,
                "timeout_s": req.timeout_s,
                "measure_memory": req.measure_memory,
                "cancelled": was_cancelled,
                "total_runs": len(df),
            }

            if not was_cancelled and not df.empty:
                saved_name = save_results(df, meta)
                meta["saved_name"] = saved_name

            raw_records = df.to_dict(orient="records") if not df.empty else []
            cleaned_rows = [_clean_row_dict(r) for r in raw_records]

            with self._lock:
                record.state = "done"
                record.rows = cleaned_rows
                record.meta = meta
        except Exception as exc:
            with self._lock:
                record.state = "error"
                record.error = {"code": "INTERNAL", "message": str(exc)}

    def get_benchmark(self, job_id: str) -> BenchRecord:
        """Retrieve a BenchRecord by ID or raise NotFoundError."""
        with self._lock:
            record = self._benchmarks.get(job_id)
            if record is None:
                raise NotFoundError(f"Benchmark job '{job_id}' not found.")
            return record

    def cancel_benchmark(self, job_id: str) -> None:
        """Cancel an ongoing benchmark job (idempotent)."""
        with self._lock:
            record = self._benchmarks.get(job_id)
            if record is not None:
                record.cancel_event.set()

    def cancel_all(self) -> None:
        """Signal cancellation to all active runs and benchmarks (e.g. on server shutdown)."""
        with self._lock:
            for rec in self._runs.values():
                rec.handle.cancel()
            for b in self._benchmarks.values():
                b.cancel_event.set()


# Singleton instance
jobs = JobManager()
