"""Backtracking search engine for CSP with limits, metrics, and state restoration."""
from __future__ import annotations

import sys
from time import perf_counter
from typing import TYPE_CHECKING, Callable

from csp.constraints import OccupancyKey
from csp.result import (
    PRESETS,
    RunControl,
    SearchConfig,
    SearchMetrics,
    SearchResult,
    SearchStatus,
)
from csp.trail import DomainState
from models.assignment import Assignment

if TYPE_CHECKING:
    from csp.problem import CSPProblem


class _Abort(Exception):
    """Internal exception raised when a limit (time, nodes) is reached or cancel is requested."""

    def __init__(self, status: SearchStatus) -> None:
        super().__init__(status.value)
        self.status = status


class _Ctx:
    """Encapsulates the mutable search context for a single run."""

    def __init__(
        self,
        problem: CSPProblem,
        config: SearchConfig,
        control: RunControl | None,
        state: DomainState,
        metrics: SearchMetrics,
        t0: float,
    ) -> None:
        self.problem = problem
        self.config = config
        self.control = control
        self.state = state
        self.assignment: dict[str, int] = {}  # session_id -> domain index
        self.used: set[OccupancyKey] = set()  # set of all occupied (resource, abs_slot) keys
        self.metrics = metrics
        self.t0 = t0
        self.propagating: bool = config.use_forward_checking or config.use_mac

    def disjoint(self, a: frozenset[OccupancyKey], b: set[OccupancyKey]) -> bool:
        """Count consistency check and test if occupancy keys are disjoint."""
        self.metrics.checks += 1
        return a.isdisjoint(b)


def _check_limits(ctx: _Ctx) -> None:
    """Verify cancellation and limits, updating progress observer if present."""
    c = ctx.control
    if c is not None and c.cancel_event.is_set():
        raise _Abort(SearchStatus.CANCELLED)

    elapsed = perf_counter() - ctx.t0
    if ctx.config.timeout_s is not None and elapsed > ctx.config.timeout_s:
        raise _Abort(SearchStatus.TIMEOUT)

    if ctx.config.node_limit is not None and ctx.metrics.nodes >= ctx.config.node_limit:
        raise _Abort(SearchStatus.NODE_LIMIT)

    if c is not None:
        c.progress.assigned = len(ctx.assignment)
        c.progress.nodes = ctx.metrics.nodes
        c.progress.attempts = ctx.metrics.attempts
        c.progress.backtracks = ctx.metrics.backtracks
        c.progress.elapsed_s = elapsed


def _select_variable_default(ctx: _Ctx) -> str:
    """Baseline variable selection: first unassigned variable in canonical sorted order."""
    for s in ctx.problem.variables:
        if s not in ctx.assignment:
            return s
    raise RuntimeError("No unassigned variables remaining")


def _order_values_default(ctx: _Ctx, sid: str) -> list[int]:
    """Baseline value ordering: natural domain order of alive values."""
    return ctx.state.alive_indices(sid)


# Pluggable hooks for heuristics (MRV, Degree, LCV) and propagation (FC, MAC)
_select_variable_fn: Callable[[_Ctx], str] = _select_variable_default
_order_values_fn: Callable[[_Ctx, str], list[int]] = _order_values_default
_forward_check_fn: Callable[[_Ctx, str, int], bool] | None = None
_mac_propagate_fn: Callable[[_Ctx, str, int], bool] | None = None
_ac3_root_fn: Callable[[_Ctx], bool] | None = None


def _search(ctx: _Ctx) -> bool:
    """Recursive chronological backtracking search."""
    _check_limits(ctx)
    ctx.metrics.nodes += 1

    if len(ctx.assignment) == len(ctx.problem.variables):
        return True  # All variables successfully assigned

    sid = _select_variable_fn(ctx)
    for i in _order_values_fn(ctx, sid):
        _check_limits(ctx)
        ctx.metrics.attempts += 1
        ks = ctx.problem.keys[sid][i]

        if not ctx.disjoint(ks, ctx.used):
            continue

        mark = ctx.state.checkpoint()
        ctx.assignment[sid] = i
        ctx.used |= ks

        ok = True
        if ctx.config.use_mac and _mac_propagate_fn is not None:
            ok = _mac_propagate_fn(ctx, sid, i)
        elif ctx.config.use_forward_checking and _forward_check_fn is not None:
            ok = _forward_check_fn(ctx, sid, i)

        if ok and _search(ctx):
            return True

        # Undo assignment and backtrack
        del ctx.assignment[sid]
        ctx.used -= ks
        ctx.state.restore(mark)
        ctx.metrics.backtracks += 1

    return False


def solve(
    problem: CSPProblem,
    config: SearchConfig | None = None,
    control: RunControl | None = None,
) -> SearchResult:
    """Solve the CSP problem using backtracking search under the specified configuration."""
    cfg = config or PRESETS["A"]
    t0 = perf_counter()
    metrics = SearchMetrics()

    # Early infeasibility: a variable has an empty initial domain
    if problem.root_wipeout is not None:
        metrics.runtime_s = perf_counter() - t0
        return SearchResult(
            status=SearchStatus.INFEASIBLE_PROVEN,
            assignment=None,
            metrics=metrics,
            config=cfg,
            message=(
                f"Session '{problem.root_wipeout}' has no allowed (day, slot, room) "
                "under unary constraints. Check room capacity, room types, and unavailability."
            ),
        )

    state = DomainState(problem)
    ctx = _Ctx(problem, cfg, control, state, metrics, t0)

    # Initialize progress observer if control provided
    if control is not None:
        control.progress.total = len(problem.variables)
        control.progress.assigned = 0
        control.progress.nodes = 0
        control.progress.attempts = 0
        control.progress.backtracks = 0
        control.progress.elapsed_s = 0.0

    # Ensure recursion depth is sufficient for deep search trees
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 3 * len(problem.variables) + 500))

    try:
        if cfg.use_ac3_root and _ac3_root_fn is not None:
            ok = _ac3_root_fn(ctx)
            if not ok:
                metrics.runtime_s = perf_counter() - t0
                return SearchResult(
                    status=SearchStatus.INFEASIBLE_PROVEN,
                    assignment=None,
                    metrics=metrics,
                    config=cfg,
                    message="AC-3 propagation emptied a domain before search: no timetable exists.",
                )

        solved = _search(ctx)
        status = SearchStatus.SOLVED if solved else SearchStatus.INFEASIBLE_PROVEN
        msg = (
            f"Valid assignment found for {len(problem.variables)} sessions."
            if solved
            else "Search finished completely; no assignment satisfies all hard constraints."
        )
    except _Abort as abort_ex:
        status = abort_ex.status
        if status == SearchStatus.TIMEOUT:
            msg = f"Time limit of {cfg.timeout_s}s reached; search inconclusive."
        elif status == SearchStatus.NODE_LIMIT:
            msg = f"Node limit of {cfg.node_limit} reached; search inconclusive."
        elif status == SearchStatus.CANCELLED:
            msg = "Search was cancelled by user."
        else:
            msg = f"Search terminated with status {status.value}."

    metrics.runtime_s = perf_counter() - t0

    # Build final assignment mapping
    assignment: dict[str, Assignment] | None = None
    if status == SearchStatus.SOLVED:
        assignment = {
            sid: problem.domains[sid][idx] for sid, idx in ctx.assignment.items()
        }

    return SearchResult(
        status=status,
        assignment=assignment,
        metrics=metrics,
        config=cfg,
        message=msg,
    )
