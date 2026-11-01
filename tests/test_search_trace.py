"""Tests for CSP search trace event recording."""
from __future__ import annotations

from data.loader import instance_from_draft, load_sample
from csp.problem import build_csp
from csp.backtracking import solve
from csp.result import SearchConfig
from csp.search_trace import TraceEventKind


def test_search_trace_recorded_when_flag_enabled() -> None:
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)
    cfg = SearchConfig(name="A", record_trace=True)

    result = solve(problem, cfg)
    assert result.status.value == "SOLVED"
    assert result.trace is not None
    assert len(result.trace) > 0
    assert not result.trace_truncated

    # Check event types present
    kinds = {e.kind for e in result.trace}
    assert "SELECT_VAR" in kinds
    assert "TRY_VALUE" in kinds
    assert "ASSIGN" in kinds


def test_search_trace_disabled_by_default() -> None:
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    problem = build_csp(instance)
    cfg = SearchConfig(name="A", record_trace=False)

    result = solve(problem, cfg)
    assert result.status.value == "SOLVED"
    assert result.trace is None
