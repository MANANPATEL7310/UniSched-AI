"""Unit tests for evaluation metrics, benchmarking matrix, and reporting."""
from __future__ import annotations

import os
import threading
from pathlib import Path
import pytest
import pandas as pd

from csp.result import PRESETS
from data.loader import instance_from_draft, load_sample
from evaluation.benchmarks import run_matrix
from evaluation.metrics import run_once, summarise
from evaluation.reports import load_results, make_report_charts, save_results


@pytest.fixture
def tiny_instance():
    draft = load_sample("tiny")
    return instance_from_draft(draft)


def test_run_once_structure_and_types(tiny_instance):
    row = run_once(tiny_instance, PRESETS["A"], measure_memory=False)

    expected_keys = [
        "instance",
        "size_label",
        "num_sessions",
        "seed",
        "algorithm",
        "status",
        "solved",
        "valid",
        "runtime_s",
        "build_s",
        "nodes",
        "attempts",
        "backtracks",
        "checks",
        "values_pruned",
        "domain_wipeouts",
        "root_pruned",
        "peak_memory_kb",
        "hard_violations",
        "soft_penalty",
        "timeout_s",
    ]
    for k in expected_keys:
        assert k in row, f"Missing key: {k}"

    assert row["instance"] == "tiny"
    assert row["algorithm"] == "A"
    assert row["solved"] is True
    assert row["valid"] is True
    assert row["nodes"] > 0
    assert row["attempts"] > 0


def test_run_once_with_memory_measurement(tiny_instance):
    row = run_once(tiny_instance, PRESETS["B"], measure_memory=True)
    assert not pd.isna(row["peak_memory_kb"])
    assert row["peak_memory_kb"] > 0


def test_summarise_aggregation(tiny_instance):
    row1 = run_once(tiny_instance, PRESETS["A"])
    row2 = run_once(tiny_instance, PRESETS["B"])
    df = pd.DataFrame([row1, row2])

    summary = summarise(df)
    assert len(summary) == 2
    assert "algorithm" in summary.columns
    assert "runtime_s" in summary.columns
    assert "runs_count" in summary.columns


def test_run_matrix_progress_and_cancel(tiny_instance):
    progress_calls = []

    def on_prog(done: int, total: int):
        progress_calls.append((done, total))

    configs = [PRESETS["A"], PRESETS["B"]]
    df = run_matrix(
        instances=[tiny_instance],
        configs=configs,
        trials=1,
        on_progress=on_prog,
    )

    assert len(df) == 2
    assert len(progress_calls) == 2
    assert progress_calls[-1] == (2, 2)

    # Test early cancellation
    cancel_evt = threading.Event()
    cancel_evt.set()  # Cancelled before start

    df_cancelled = run_matrix(
        instances=[tiny_instance],
        configs=configs,
        cancel_event=cancel_evt,
    )
    assert len(df_cancelled) == 0


def test_save_and_load_results(tiny_instance, tmp_path):
    row = run_once(tiny_instance, PRESETS["A"])
    df = pd.DataFrame([row])
    meta = {"test": True, "version": "1.0"}

    base_name = save_results(df, meta, folder=str(tmp_path))
    assert (tmp_path / f"{base_name}.csv").exists()
    assert (tmp_path / f"{base_name}.json").exists()

    loaded_df = load_results(str(tmp_path / f"{base_name}.csv"))
    assert len(loaded_df) == 1
    assert loaded_df["instance"].iloc[0] == "tiny"


def test_make_report_charts(tiny_instance, tmp_path):
    row_a = run_once(tiny_instance, PRESETS["A"])
    row_c = run_once(tiny_instance, PRESETS["C"])
    df = pd.DataFrame([row_a, row_c])

    charts = make_report_charts(df, out_dir=str(tmp_path))
    assert len(charts) > 0
    for chart_path in charts:
        assert Path(chart_path).exists()
        assert os.path.getsize(chart_path) > 0
