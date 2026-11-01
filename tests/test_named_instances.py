"""Unit tests verifying that all named sample instances load, validate, and have expected metadata."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from data.loader import list_samples, load_sample, instance_from_draft
from data.validator import validate_instance
from csp.problem import build_csp

NAMED_INSTANCES = [
    "feasible_obvious",
    "multi_solution",
    "tight",
    "impossible",
    "multihour_lab",
    "unavailability",
]


def test_list_samples_includes_all_named_instances():
    samples = list_samples()
    names = {s.name for s in samples}
    assert "tiny" in names
    for name in NAMED_INSTANCES:
        assert name in names, f"Sample '{name}' missing from list_samples()"


@pytest.mark.parametrize("name", NAMED_INSTANCES + ["tiny"])
def test_named_instance_loads_and_has_metadata(name: str):
    folder = Path("data/sample_data") / name
    assert (folder / "info.json").exists(), f"{name} is missing info.json"
    assert (folder / "expected.json").exists(), f"{name} is missing expected.json"
    assert (folder / "README.md").exists(), f"{name} is missing README.md"

    expected = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    assert "expected_status" in expected
    assert expected["expected_status"] in ("SOLVED", "INFEASIBLE_PROVEN")

    draft = load_sample(name)
    assert draft["name"] == name
    inst = instance_from_draft(draft)
    assert inst.name == name
    assert len(inst.sessions) > 0

    # Input validation check
    issues = validate_instance(inst)
    errors = [i for i in issues if i.severity == "ERROR"]
    assert len(errors) == 0, f"Instance {name} has unexpected input errors: {errors}"

    # Verify CSP problem builds cleanly without raising
    problem = build_csp(inst)
    assert len(problem.variables) == len(inst.sessions)
    assert all(len(dom) >= 0 for dom in problem.domains.values())


def test_impossible_instance_properties():
    draft = load_sample("impossible")
    inst = instance_from_draft(draft)
    problem = build_csp(inst)

    # Both sessions should have non-empty root domains
    assert len(problem.domains["X|A|1"]) == 2
    assert len(problem.domains["X|A|2"]) == 2
    assert problem.root_wipeout is None

    # But they must conflict on all assignments because T01 is only free at Mon@09:00
    for i1 in range(len(problem.domains["X|A|1"])):
        for i2 in range(len(problem.domains["X|A|2"])):
            assert problem.conflicts("X|A|1", i1, "X|A|2", i2) is True


def test_unavailability_instance_forces_domains():
    draft = load_sample("unavailability")
    inst = instance_from_draft(draft)
    problem = build_csp(inst)

    # Both variables should have domain size exactly 1
    assert len(problem.domains["C01|A|1"]) == 1
    assert len(problem.domains["C02|B|1"]) == 1
