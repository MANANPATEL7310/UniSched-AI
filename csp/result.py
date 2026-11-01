"""Search result types, presets, and metrics for the CSP engine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading
from typing import TYPE_CHECKING

from models.assignment import Assignment

if TYPE_CHECKING:
    from csp.search_trace import TraceEvent


class SearchStatus(Enum):
    """Possible termination states of the CSP search."""

    SOLVED = "SOLVED"
    INFEASIBLE_PROVEN = "INFEASIBLE_PROVEN"
    TIMEOUT = "TIMEOUT"
    NODE_LIMIT = "NODE_LIMIT"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class SearchConfig:
    """Algorithm configuration specifying heuristics, propagation, and limits."""

    name: str = "A"
    use_mrv: bool = False
    use_degree: bool = False
    use_lcv: bool = False
    use_forward_checking: bool = False
    use_ac3_root: bool = False
    use_mac: bool = False  # if True, FC pruning runs inside MAC; do not set both flags separately
    timeout_s: float | None = 60.0
    node_limit: int | None = None
    record_trace: bool = False  # optional extension


PRESETS: dict[str, SearchConfig] = {
    "A": SearchConfig(name="A"),
    "B": SearchConfig(name="B", use_mrv=True, use_degree=True, use_lcv=True),
    "C": SearchConfig(
        name="C",
        use_mrv=True,
        use_degree=True,
        use_lcv=True,
        use_forward_checking=True,
    ),
    "D": SearchConfig(
        name="D",
        use_mrv=True,
        use_degree=True,
        use_lcv=True,
        use_ac3_root=True,
        use_mac=True,
    ),
}


@dataclass
class SearchMetrics:
    """Quantitative performance counters collected during search."""

    nodes: int = 0
    attempts: int = 0
    backtracks: int = 0
    checks: int = 0  # consistency checks (isdisjoint)
    values_pruned: int = 0  # values removed by FC/AC-3/MAC during search
    root_pruned: int = 0  # values removed by AC-3 before search
    domain_wipeouts: int = 0
    runtime_s: float = 0.0
    build_s: float = 0.0
    peak_memory_kb: int | None = None


@dataclass
class ProgressState:
    """Thread-safe snapshot of search progress communicated to the API."""

    total: int = 0
    assigned: int = 0
    nodes: int = 0
    attempts: int = 0
    backtracks: int = 0
    elapsed_s: float = 0.0


@dataclass
class RunControl:
    """Cancellation handle and progress observer for background solver threads."""

    cancel_event: threading.Event
    progress: ProgressState


@dataclass
class SearchResult:
    """Final outcome returned by solve()."""

    status: SearchStatus
    assignment: dict[str, Assignment] | None  # complete ONLY when SOLVED, else None
    metrics: SearchMetrics
    config: SearchConfig
    message: str
    trace: list[TraceEvent] | None = None
    trace_truncated: bool = False
