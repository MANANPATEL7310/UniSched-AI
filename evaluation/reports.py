"""Benchmark reporting, CSV/JSON persistence, and chart generation."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

# Ensure matplotlib uses temporary cache dir and headless Agg backend
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def make_report_charts(df: pd.DataFrame, out_dir: str) -> list[str]:
    """Generate high-resolution PNG summary charts from benchmark results for the project report.

    Args:
        df: DataFrame produced by run_matrix containing benchmark metrics.
        out_dir: Target directory path to write generated PNG files.

    Returns:
        List of generated file paths.
    """
    if df.empty:
        return []

    target_path = Path(out_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    # Filter to solved rows for runtime/performance charts
    valid_df = df[df["solved"] == True] if "solved" in df.columns else df
    plot_df = valid_df if not valid_df.empty else df

    # Color mapping for algorithms A, B, C, D
    algo_colors = {
        "A": "#94a3b8",  # slate/gray
        "B": "#3b82f6",  # blue
        "C": "#10b981",  # emerald green
        "D": "#8b5cf6",  # purple
    }

    # Chart 1: Runtime Comparison by Algorithm and Size
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        pivot_runtime = plot_df.pivot_table(
            index="size_label",
            columns="algorithm",
            values="runtime_s",
            aggfunc="mean",
        )
        # Ensure ordered size labels
        size_order = [s for s in ["tiny", "small", "medium", "large"] if s in pivot_runtime.index]
        if size_order:
            pivot_runtime = pivot_runtime.reindex(size_order)

        pivot_runtime.plot(
            kind="bar",
            ax=ax,
            color=[algo_colors.get(c, "#64748b") for c in pivot_runtime.columns],
            width=0.7,
        )
        ax.set_title("Mean Search Runtime (s) by Algorithm and Problem Size", fontsize=12, fontweight="bold")
        ax.set_xlabel("Problem Size", fontsize=10)
        ax.set_ylabel("Runtime (seconds)", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()

        p1 = str(target_path / "runtime_comparison.png")
        fig.savefig(p1, dpi=200)
        plt.close(fig)
        generated.append(p1)
    except Exception as e:
        plt.close("all")

    # Chart 2: Search Nodes Visited (Log Scale)
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        pivot_nodes = plot_df.pivot_table(
            index="size_label",
            columns="algorithm",
            values="nodes",
            aggfunc="mean",
        )
        size_order = [s for s in ["tiny", "small", "medium", "large"] if s in pivot_nodes.index]
        if size_order:
            pivot_nodes = pivot_nodes.reindex(size_order)

        pivot_nodes.plot(
            kind="bar",
            ax=ax,
            color=[algo_colors.get(c, "#64748b") for c in pivot_nodes.columns],
            width=0.7,
            logy=True,
        )
        ax.set_title("Mean Search Nodes Visited (Log Scale)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Problem Size", fontsize=10)
        ax.set_ylabel("Nodes (log scale)", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()

        p2 = str(target_path / "nodes_comparison.png")
        fig.savefig(p2, dpi=200)
        plt.close(fig)
        generated.append(p2)
    except Exception as e:
        plt.close("all")

    # Chart 3: Backtracks Comparison
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        pivot_bt = plot_df.pivot_table(
            index="size_label",
            columns="algorithm",
            values="backtracks",
            aggfunc="mean",
        )
        size_order = [s for s in ["tiny", "small", "medium", "large"] if s in pivot_bt.index]
        if size_order:
            pivot_bt = pivot_bt.reindex(size_order)

        pivot_bt.plot(
            kind="bar",
            ax=ax,
            color=[algo_colors.get(c, "#64748b") for c in pivot_bt.columns],
            width=0.7,
        )
        ax.set_title("Mean Backtracks by Algorithm and Size", fontsize=12, fontweight="bold")
        ax.set_xlabel("Problem Size", fontsize=10)
        ax.set_ylabel("Backtracks", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()

        p3 = str(target_path / "backtracks_comparison.png")
        fig.savefig(p3, dpi=200)
        plt.close(fig)
        generated.append(p3)
    except Exception as e:
        plt.close("all")

    # Chart 4: Values Pruned during Propagation (Algorithms C & D)
    try:
        if "values_pruned" in plot_df.columns:
            fig, ax = plt.subplots(figsize=(8, 5))
            cd_df = plot_df[plot_df["algorithm"].isin(["C", "D"])]
            if not cd_df.empty:
                pivot_prune = cd_df.pivot_table(
                    index="size_label",
                    columns="algorithm",
                    values="values_pruned",
                    aggfunc="mean",
                )
                pivot_prune.plot(
                    kind="bar",
                    ax=ax,
                    color=[algo_colors.get(c, "#10b981") for c in pivot_prune.columns],
                    width=0.5,
                )
                ax.set_title("Mean Values Pruned by Forward Checking (C) and MAC (D)", fontsize=12, fontweight="bold")
                ax.set_xlabel("Problem Size", fontsize=10)
                ax.set_ylabel("Values Pruned", fontsize=10)
                ax.grid(axis="y", linestyle="--", alpha=0.5)
                plt.tight_layout()

                p4 = str(target_path / "pruning_comparison.png")
                fig.savefig(p4, dpi=200)
                plt.close(fig)
                generated.append(p4)
    except Exception as e:
        plt.close("all")

    return generated


def save_results(df: pd.DataFrame, meta: dict[str, Any], folder: str = "results") -> str:
    """Save benchmark results to timestamped CSV and JSON files in results folder.

    Returns:
        The generated file basename (e.g. '20261101_130000').
    """
    target_dir = Path(folder)
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = target_dir / f"{base_name}.csv"
    json_file = target_dir / f"{base_name}.json"

    df.to_csv(csv_file, index=False)
    json_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return base_name


def load_results(path: str) -> pd.DataFrame:
    """Load benchmark DataFrame from a CSV file path or base name."""
    p = Path(path)
    if not p.suffix:
        p = p.with_suffix(".csv")
    if not p.exists():
        # Check if located inside results folder
        p_res = Path("results") / p.name
        if p_res.exists():
            p = p_res
        else:
            raise FileNotFoundError(f"Benchmark results file '{path}' not found.")

    return pd.read_csv(p)

