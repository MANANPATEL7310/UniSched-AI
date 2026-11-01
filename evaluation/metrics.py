"""Benchmark run metrics calculation and aggregation."""
from __future__ import annotations

import math
import threading
import tracemalloc
from typing import TYPE_CHECKING, Any

import pandas as pd

from csp.problem import build_csp
from csp.result import RunControl, SearchConfig, SearchStatus
from scheduling.scheduler import generate_timetable

if TYPE_CHECKING:
    from models.instance import SchedulingInstance


def _infer_size_label(instance: SchedulingInstance) -> str:
    """Infer instance size label ('small', 'medium', 'large', 'tiny') from meta or session count."""
    meta = instance.meta or {}
    gen_cfg = meta.get("generator_config")
    if isinstance(gen_cfg, dict) and "name" in gen_cfg:
        return str(gen_cfg["name"])
    if "size_label" in meta:
        return str(meta["size_label"])

    name_lower = instance.name.lower()
    for label in ("tiny", "small", "medium", "large"):
        if label in name_lower:
            return label

    n = len(instance.sessions)
    if n <= 10:
        return "tiny"
    elif n <= 60:
        return "small"
    elif n <= 180:
        return "medium"
    return "large"


def run_once(
    instance: SchedulingInstance,
    config: SearchConfig,
    measure_memory: bool = False,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Execute a single solve trial on an instance under config and return a benchmark metric dict.

    If measure_memory is True, performs a separate second execution with tracemalloc
    so memory profiling overhead does not distort the reported runtime_s.
    """
    control = RunControl(cancel_event=cancel_event) if cancel_event is not None else None
    outcome = generate_timetable(instance, config, control=control)

    peak_memory_kb: float = float("nan")
    if measure_memory and not (cancel_event and cancel_event.is_set()):
        try:
            tracemalloc.start()
            prob = build_csp(instance)
            from csp.backtracking import solve
            _ = solve(prob, config)
            _, peak = tracemalloc.get_traced_memory()
            peak_memory_kb = round(peak / 1024.0, 2)
        finally:
            tracemalloc.stop()

    hard_violations = len(outcome.validation.violations) if outcome.validation else 0
    soft_score = outcome.soft.total if outcome.soft is not None else float("nan")
    seed = instance.meta.get("generator_config", {}).get("seed", 0) if instance.meta else 0

    return {
        "instance": instance.name,
        "size_label": _infer_size_label(instance),
        "num_sessions": len(instance.sessions),
        "seed": seed,
        "algorithm": config.name,
        "status": outcome.status.value,
        "solved": outcome.status == SearchStatus.SOLVED,
        "valid": bool(outcome.is_valid),
        "runtime_s": round(outcome.runtime_s, 6),
        "build_s": round(outcome.build_s, 6),
        "nodes": outcome.metrics.nodes,
        "attempts": outcome.metrics.attempts,
        "backtracks": outcome.metrics.backtracks,
        "checks": outcome.metrics.checks,
        "values_pruned": outcome.metrics.values_pruned,
        "domain_wipeouts": outcome.metrics.domain_wipeouts,
        "root_pruned": outcome.metrics.root_pruned,
        "peak_memory_kb": peak_memory_kb,
        "hard_violations": hard_violations,
        "soft_penalty": soft_score,
        "timeout_s": config.timeout_s if config.timeout_s is not None else float("nan"),
    }


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """Compute summary aggregations (means, success rate) grouped by (size_label, algorithm)."""
    if df.empty:
        return pd.DataFrame()

    group_cols = ["size_label", "algorithm"]
    numeric_cols = [
        "num_sessions",
        "runtime_s",
        "build_s",
        "nodes",
        "attempts",
        "backtracks",
        "checks",
        "values_pruned",
        "domain_wipeouts",
        "root_pruned",
        "hard_violations",
        "soft_penalty",
    ]
    available_numeric = [c for c in numeric_cols if c in df.columns]

    agg_dict: dict[str, Any] = {c: "mean" for c in available_numeric}
    if "solved" in df.columns:
        agg_dict["solved"] = "mean"
    if "valid" in df.columns:
        agg_dict["valid"] = "mean"

    summary = df.groupby(group_cols, as_index=False).agg(agg_dict)
    summary["runs_count"] = df.groupby(group_cols).size().values
    return summary
