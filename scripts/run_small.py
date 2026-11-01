#!/usr/bin/env python3
"""CLI utility to execute Config A search on small and named instances."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from csp.result import PRESETS
from data.loader import instance_from_draft, list_samples, load_sample
from scheduling.scheduler import generate_timetable


def run_instance(name: str, verbose: bool = True) -> bool:
    """Run search on a single sample instance and verify outcome against expected.json."""
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Running Config A on: {name}")
        print(f"{'=' * 60}")

    try:
        draft = load_sample(name)
        instance = instance_from_draft(draft)
    except Exception as e:
        print(f"  [ERROR] Failed to load sample '{name}': {e}")
        return False

    expected_status: str | None = None
    expected_file = Path("data/sample_data") / name / "expected.json"
    if expected_file.exists():
        try:
            expected_data = json.loads(expected_file.read_text(encoding="utf-8"))
            expected_status = expected_data.get("expected_status")
        except Exception:
            pass

    outcome = generate_timetable(instance, PRESETS["A"])
    status_str = outcome.status.value

    print(f"  Status:       {status_str}")
    print(f"  Valid:        {outcome.is_valid}")
    print(f"  Runtime:      {outcome.runtime_s:.4f}s (Build: {outcome.build_s:.4f}s)")
    print(f"  Nodes:        {outcome.metrics.nodes:,}")
    print(f"  Attempts:     {outcome.metrics.attempts:,}")
    print(f"  Backtracks:   {outcome.metrics.backtracks:,}")
    print(f"  Checks:       {outcome.metrics.checks:,}")
    print(f"  Message:      {outcome.message}")

    match_ok = True
    if expected_status:
        if status_str == expected_status:
            print(f"  Outcome:      MATCHES EXPECTED ({expected_status})")
        else:
            print(f"  Outcome:      MISMATCH! Expected: {expected_status}, Got: {status_str}")
            match_ok = False

    if status_str == "SOLVED" and not outcome.is_valid:
        print("  CRITICAL: Solver claimed SOLVED but timetable validator rejected solution!")
        match_ok = False

    return match_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Config A timetable search.")
    parser.add_argument(
        "--sample",
        type=str,
        default="tiny",
        help="Specific sample folder name to run, or 'all'",
    )
    args = parser.parse_args()

    if args.sample == "all":
        samples = list_samples()
        all_ok = True
        for s in samples:
            ok = run_instance(s.name)
            if not ok:
                all_ok = False
        return 0 if all_ok else 1
    else:
        ok = run_instance(args.sample)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
