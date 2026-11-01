"""Soft-constraint local optimization using hill-climbing search with strict hard constraint invariance.

Explores conflict-free reassignments and equal-duration swaps to minimize:
- Student gaps between sessions on the same day.
- Teacher gaps between sessions on the same day.
- Teacher daily workload balance.
- Teacher time slot preferences.

INVARIANT:
Every accepted candidate move or swap is strictly verified by the independent
validate_timetable function; zero hard conflicts are tolerated at any time.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from csp.domains import build_domains
from csp.problem import build_csp
from models.assignment import Assignment
from models.instance import SchedulingInstance
from models.timetable import Timetable
from scheduling.soft_constraints import SoftReport, SoftWeights, soft_penalty
from scheduling.timetable_validator import ValidationReport, validate_timetable


@dataclass
class SoftImprovementOutcome:
    """Outcome of a soft constraint local search optimization run."""

    status: str
    initial_penalty: float
    improved_penalty: float
    steps_accepted: int
    timetable: Timetable
    report: SoftReport
    validation: ValidationReport
    message: str


def improve_soft_constraints(
    instance: SchedulingInstance,
    timetable: Timetable,
    max_steps: int = 150,
    time_limit_s: float = 3.0,
    weights: SoftWeights = SoftWeights(),
) -> SoftImprovementOutcome:
    """Optimize soft constraints on an existing valid timetable using hill-climbing local search.

    Args:
        instance: Base scheduling problem instance.
        timetable: Currently valid solution timetable.
        max_steps: Maximum iterations/moves to evaluate.
        time_limit_s: Wall-clock execution time limit.
        weights: Configurable weights for soft penalty terms.

    Returns:
        SoftImprovementOutcome containing the optimized timetable and penalty delta.
    """
    t0 = perf_counter()

    # 1. Independent validation of initial timetable
    initial_val = validate_timetable(instance, timetable)
    if not initial_val.is_valid:
        raise ValueError(
            "Cannot optimize soft constraints on an invalid timetable. "
            f"Found {len(initial_val.violations)} hard constraint violations."
        )

    current_assignment = dict(timetable.assignment)
    initial_report = soft_penalty(instance, current_assignment, weights=weights)
    initial_penalty = initial_report.total
    current_report = initial_report
    current_penalty = initial_report.total

    domains = build_domains(instance)
    csp_prob = build_csp(instance)
    session_map = {s.session_id: s for s in instance.sessions}
    sessions = list(instance.sessions)

    steps_accepted = 0

    # Iterative hill climbing
    improved_in_pass = True
    step_count = 0

    while improved_in_pass and step_count < max_steps:
        improved_in_pass = False

        if perf_counter() - t0 > time_limit_s:
            break

        # Pass 1: Single-session move search
        for s in sessions:
            if step_count >= max_steps or perf_counter() - t0 > time_limit_s:
                break

            sid = s.session_id
            curr_asgn = current_assignment[sid]
            cand_values = domains.get(sid, [])

            # Filter candidate values that differ from current assignment
            for cand in cand_values:
                step_count += 1
                if step_count >= max_steps or perf_counter() - t0 > time_limit_s:
                    break

                if cand == curr_asgn:
                    continue

                # Test trial assignment
                trial_assignment = dict(current_assignment)
                trial_assignment[sid] = cand

                trial_timetable = Timetable(instance, trial_assignment)
                val_check = validate_timetable(instance, trial_timetable)

                if val_check.is_valid:
                    trial_report = soft_penalty(instance, trial_assignment, weights=weights)
                    if trial_report.total < current_penalty:
                        current_assignment = trial_assignment
                        current_report = trial_report
                        current_penalty = trial_report.total
                        steps_accepted += 1
                        improved_in_pass = True
                        break  # Greedily move to next session

        # Pass 2: Equal-duration 2-session swaps
        for i in range(len(sessions)):
            if step_count >= max_steps or perf_counter() - t0 > time_limit_s:
                break
            s1 = sessions[i]
            for j in range(i + 1, len(sessions)):
                if step_count >= max_steps or perf_counter() - t0 > time_limit_s:
                    break
                s2 = sessions[j]

                if s1.duration_slots != s2.duration_slots:
                    continue

                asgn1 = current_assignment[s1.session_id]
                asgn2 = current_assignment[s2.session_id]

                if asgn1 == asgn2:
                    continue

                step_count += 1

                # Try swapping asgn1 and asgn2
                trial_assignment = dict(current_assignment)
                trial_assignment[s1.session_id] = asgn2
                trial_assignment[s2.session_id] = asgn1

                trial_timetable = Timetable(instance, trial_assignment)
                val_check = validate_timetable(instance, trial_timetable)

                if val_check.is_valid:
                    trial_report = soft_penalty(instance, trial_assignment, weights=weights)
                    if trial_report.total < current_penalty:
                        current_assignment = trial_assignment
                        current_report = trial_report
                        current_penalty = trial_report.total
                        steps_accepted += 1
                        improved_in_pass = True
                        break

    final_timetable = Timetable(instance, current_assignment)
    final_val = validate_timetable(instance, final_timetable)
    status_str = "IMPROVED" if steps_accepted > 0 else "UNCHANGED"
    msg = (
        f"Soft optimization complete. Penalty reduced from {initial_penalty:.1f} to {current_penalty:.1f} "
        f"across {steps_accepted} accepted move(s)."
        if steps_accepted > 0
        else f"No soft constraint improvements found; timetable already at local optimum ({initial_penalty:.1f})."
    )

    return SoftImprovementOutcome(
        status=status_str,
        initial_penalty=initial_report.total,
        improved_penalty=current_report.total,
        steps_accepted=steps_accepted,
        timetable=final_timetable,
        report=current_report,
        validation=final_val,
        message=msg,
    )
