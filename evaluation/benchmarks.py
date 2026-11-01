"""Benchmark matrix execution across instances, algorithms, and trials."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable

import pandas as pd

from csp.result import SearchConfig
from evaluation.metrics import run_once

if TYPE_CHECKING:
    from models.instance import SchedulingInstance


def run_matrix(
    instances: list[SchedulingInstance],
    configs: list[SearchConfig],
    trials: int = 1,
    on_progress: Callable[[int, int], None] | None = None,
    measure_memory: bool = False,
    cancel_event: threading.Event | None = None,
) -> pd.DataFrame:
    """Run cross-product benchmark of instances and configurations across trials.

    Args:
        instances: List of SchedulingInstance objects to evaluate.
        configs: List of SearchConfig algorithm presets.
        trials: Repetitions per (instance, config) pair.
        on_progress: Optional callback invoked with (done: int, total: int).
        measure_memory: If True, measures peak memory in a separate second run.
        cancel_event: Optional threading.Event to abort the benchmark loop early.

    Returns:
        DataFrame where each row represents a single benchmark trial run.
    """
    total = len(instances) * len(configs) * max(1, trials)
    done = 0
    rows: list[dict] = []

    for trial in range(trials):
        for instance in instances:
            for cfg in configs:
                if cancel_event is not None and cancel_event.is_set():
                    # Aborted: do not include aborted row, return partial results
                    return pd.DataFrame(rows)

                row = run_once(
                    instance=instance,
                    config=cfg,
                    measure_memory=measure_memory,
                    cancel_event=cancel_event,
                )

                if cancel_event is not None and cancel_event.is_set():
                    # If cancelled during run_once, drop row and return immediately
                    return pd.DataFrame(rows)

                rows.append(row)
                done += 1
                if on_progress is not None:
                    on_progress(done, total)

    return pd.DataFrame(rows)

