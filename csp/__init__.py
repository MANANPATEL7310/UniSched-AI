"""CSP package for University Course Timetabling."""
from __future__ import annotations

from csp.backtracking import solve
from csp.constraints import OccupancyKey, occupancy_keys, unary_ok
from csp.domains import build_domains
from csp.heuristics import count_legal, lcv_score, order_values, select_variable
from csp.problem import CSPProblem, build_csp
from csp.result import (
    PRESETS,
    ProgressState,
    RunControl,
    SearchConfig,
    SearchMetrics,
    SearchResult,
    SearchStatus,
)
from csp.trail import DomainState

__all__ = [
    "SearchStatus",
    "SearchConfig",
    "PRESETS",
    "SearchMetrics",
    "ProgressState",
    "RunControl",
    "SearchResult",
    "OccupancyKey",
    "unary_ok",
    "occupancy_keys",
    "build_domains",
    "CSPProblem",
    "build_csp",
    "DomainState",
    "solve",
    "count_legal",
    "select_variable",
    "lcv_score",
    "order_values",
]





