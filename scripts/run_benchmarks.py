#!/usr/bin/env python3
"""CLI utility to execute the benchmark matrix and generate persistent CSV/JSON/PNG results."""
from __future__ import annotations

import argparse
from dataclasses import replace
import platform
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from csp.result import PRESETS as ALGO_PRESETS, SearchConfig
from data.generator import PRESETS as INSTANCE_PRESETS, generate_instance
from evaluation.benchmarks import run_matrix
from evaluation.reports import make_report_charts, save_results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run benchmark matrix across instance sizes and CSP algorithms.")
    parser.add_argument(
        "--sizes",
        nargs="+",
        default=["small"],
        choices=["small", "medium", "large"],
        help="Instance size presets to test (default: small)",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=["A", "B", "C", "D"],
        choices=["A", "B", "C", "D"],
        help="Algorithms to benchmark (default: A B C D)",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=1,
        help="Number of random seeds per size (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Search timeout per run in seconds (default: 60.0)",
    )
    parser.add_argument(
        "--output-folder",
        type=str,
        default="results",
        help="Folder to save benchmark CSV/JSON and charts (default: results)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("UniSched-AI — CSP Algorithm Benchmark Matrix Runner")
    print("=" * 70)
    print(f"Sizes:      {args.sizes}")
    print(f"Algorithms: {args.algorithms}")
    print(f"Seeds:      {args.seeds}")
    print(f"Timeout:    {args.timeout}s")
    print(f"Target:     {args.output_folder}")
    print("-" * 70)

    # 1. Build instances
    instances = []
    for sz in args.sizes:
        base_cfg = INSTANCE_PRESETS[sz]
        for s in range(args.seeds):
            cfg = replace(base_cfg, seed=s)
            print(f"Generating synthetic instance: size={sz}, seed={s}...")
            inst = generate_instance(cfg)
            instances.append(inst)

    # 2. Build configs
    configs = []
    for algo in args.algorithms:
        base_search_cfg = ALGO_PRESETS[algo]
        search_cfg = replace(base_search_cfg, timeout_s=args.timeout)
        configs.append(search_cfg)

    # 3. Progress callback
    def on_progress(done: int, total: int):
        pct = (done / total) * 100
        print(f"Progress: [{done}/{total}] ({pct:.1f}%) completed...")

    # 4. Run matrix
    print("\nExecuting benchmark matrix...")
    t0 = time.perf_counter()
    df = run_matrix(
        instances=instances,
        configs=configs,
        trials=1,
        on_progress=on_progress,
        measure_memory=False,
    )
    elapsed = time.perf_counter() - t0
    print(f"\nBenchmark matrix completed in {elapsed:.2f}s ({len(df)} total runs).")

    # 5. Metadata
    meta = {
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform.platform(),
        "python": sys.version,
        "sizes": args.sizes,
        "algorithms": args.algorithms,
        "seeds": args.seeds,
        "timeout_s": args.timeout,
        "total_runs": len(df),
        "elapsed_s": round(elapsed, 3),
    }

    # 6. Save results
    base_name = save_results(df, meta, folder=args.output_folder)
    print(f"\nSaved CSV & JSON results to: {args.output_folder}/{base_name}.(csv|json)")

    # 7. Generate report charts
    chart_dir = str(Path(args.output_folder) / "charts")
    charts = make_report_charts(df, out_dir=chart_dir)
    if charts:
        print(f"Generated {len(charts)} PNG report charts in {chart_dir}:")
        for c in charts:
            print(f"  - {c}")

    # 8. Display terminal summary table
    print("\nSummary Table:")
    cols = ["size_label", "algorithm", "status", "solved", "runtime_s", "nodes", "backtracks", "values_pruned"]
    available_cols = [c for c in cols if c in df.columns]
    print(df[available_cols].to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())

