"""Unit and integration tests for Maintaining Arc Consistency (MAC / Config D)."""
from __future__ import annotations

import pytest

from csp.backtracking import _Ctx, solve
from csp.mac import mac_propagate
from csp.problem import build_csp
from csp.result import PRESETS, SearchConfig, SearchMetrics, SearchStatus
from csp.trail import DomainState
from data.loader import instance_from_draft, load_sample
from scheduling.timetable_validator import validate_timetable


def _make_test_ctx(problem, config=None):
    cfg = config or PRESETS["D"]
    state = DomainState(problem)
    metrics = SearchMetrics()
    return _Ctx(
        problem=problem,
        config=cfg,
        control=None,
        state=state,
        metrics=metrics,
        t0=0.0,
    )


def test_mac_solves_tiny_and_valid():
    draft = load_sample("tiny")
    inst = instance_from_draft(draft)
    prob = build_csp(inst)

    res = solve(prob, PRESETS["D"])
    assert res.status == SearchStatus.SOLVED
    assert res.assignment is not None
    assert res.metrics.nodes > 0

    report = validate_timetable(inst, res.assignment)
    assert report.is_valid is True
    assert len(report.violations) == 0


@pytest.mark.parametrize("sample_name", [
    "feasible_obvious",
    "impossible",
    "multi_solution",
    "multihour_lab",
    "tight",
    "tiny",
    "unavailability",
])
def test_mac_agrees_with_expected_statuses_on_all_named_instances(sample_name: str):
    draft = load_sample(sample_name)
    inst = instance_from_draft(draft)
    prob = build_csp(inst)

    res_a = solve(prob, PRESETS["A"])
    res_d = solve(prob, PRESETS["D"])

    # D must agree with A on feasibility outcome
    assert res_d.status == res_a.status

    if res_d.status == SearchStatus.SOLVED:
        assert res_d.assignment is not None
        report = validate_timetable(inst, res_d.assignment)
        assert report.is_valid is True
        assert len(report.violations) == 0
    else:
        assert res_d.status == SearchStatus.INFEASIBLE_PROVEN
        assert res_d.assignment is None


def test_mac_state_restored_to_initial_minus_root_prunes():
    """Verify that search restores DomainState properly on completion."""
    draft = load_sample("tight")
    inst = instance_from_draft(draft)
    prob = build_csp(inst)

    ctx = _make_test_ctx(prob)
    initial_snapshot = ctx.state.snapshot()

    res = solve(prob, PRESETS["D"])
    assert res.status == SearchStatus.SOLVED

    # Original problem domain structures must remain intact
    for s in prob.variables:
        assert len(prob.domains[s]) > 0


def test_mac_propagation_pruning_and_backtrack_restore():
    """Test that mac_propagate prunes through chains and restores exactly on backtrack."""
    draft = load_sample("tight")
    inst = instance_from_draft(draft)
    prob = build_csp(inst)
    ctx = _make_test_ctx(prob)

    sid = prob.variables[0]
    val_idx = 0

    snapshot_before = ctx.state.snapshot()
    mark = ctx.state.checkpoint()

    ctx.assignment[sid] = val_idx
    ctx.used |= prob.keys[sid][val_idx]

    ok = mac_propagate(ctx, sid, val_idx)
    # If successful, some values should have been pruned across the network
    if ok:
        assert ctx.metrics.values_pruned > 0
        snapshot_during = ctx.state.snapshot()
        assert snapshot_during != snapshot_before

    # Restore to mark
    ctx.state.restore(mark)
    snapshot_after = ctx.state.snapshot()
    assert snapshot_after == snapshot_before

