"""Architectural boundary tests enforcing module separation rules.

Rules enforced:
1. scheduling/timetable_validator.py and models/ must not import anything from csp/.
2. Package csp/ must import only the standard library and models/ (no pandas, fastapi, pydantic, matplotlib).
3. Package models/ must have no top-level imports of pandas, fastapi, pydantic, or matplotlib.
4. Nothing outside api/ (excluding tests and dev scripts) may import fastapi.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _get_imports(path: Path) -> list[tuple[int, str]]:
    """Parse a Python source file and extract all imported module names with line numbers."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                module_imports.append((node.lineno, a.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_imports.append((node.lineno, node.module))
    return module_imports


def test_validator_and_models_import_no_csp():
    """Independent validator and domain models must never import from the solver engine."""
    # Check scheduling/timetable_validator.py
    validator_path = Path("scheduling/timetable_validator.py")
    for lineno, module in _get_imports(validator_path):
        assert not module.startswith("csp"), f"{validator_path}:{lineno} illegal import of '{module}'"

    # Check models/*.py
    for model_path in Path("models").glob("*.py"):
        for lineno, module in _get_imports(model_path):
            assert not module.startswith("csp"), f"{model_path}:{lineno} illegal import of '{module}'"


def test_csp_engine_imports_no_heavy_frameworks():
    """Package csp/ imports only standard library and models (no pandas/fastapi/pydantic/matplotlib)."""
    banned = ("pandas", "fastapi", "pydantic", "matplotlib")
    for csp_path in Path("csp").glob("*.py"):
        for lineno, module in _get_imports(csp_path):
            for b in banned:
                assert not module.startswith(b), (
                    f"{csp_path}:{lineno} illegal import of '{module}' (csp must remain pure standard library)"
                )


def test_models_have_no_toplevel_framework_imports():
    """Models must not import pandas, fastapi, pydantic, or matplotlib at module top level."""
    banned = ("pandas", "fastapi", "pydantic", "matplotlib")
    for model_path in Path("models").glob("*.py"):
        tree = ast.parse(model_path.read_text(encoding="utf-8"), filename=str(model_path))
        for node in tree.body:
            if isinstance(node, ast.Import):
                for a in node.names:
                    for b in banned:
                        assert not a.name.startswith(b), (
                            f"{model_path}:{node.lineno} top-level import of '{a.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for b in banned:
                        assert not node.module.startswith(b), (
                            f"{model_path}:{node.lineno} top-level import from '{node.module}'"
                        )


def test_nothing_outside_api_imports_fastapi():
    """Only the api package (plus tests/scripts) may import FastAPI."""
    root = Path(".")
    ignored_dirs = {".venv", "node_modules", "api", "tests", "scripts"}
    for py_file in root.rglob("*.py"):
        if any(part in py_file.parts for part in ignored_dirs):
            continue
        for lineno, module in _get_imports(py_file):
            assert not module.startswith("fastapi"), (
                f"{py_file}:{lineno} illegal import of 'fastapi' outside api package"
            )
