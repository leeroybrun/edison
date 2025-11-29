from __future__ import annotations

import importlib
import sys
from itertools import permutations
from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root


def test_backward_compatible_imports() -> None:
    """Public API should stay import-compatible after splitting into a package."""
    from edison.core.qa.validator import (  # type: ignore
        validate_dimension_weights,
        simple_delegation_hint,
        enhance_delegation_hint,
        build_validator_roster,
        process_validator_template,
        run_validator,
    )

    exported = {
        "validate_dimension_weights": validate_dimension_weights,
        "simple_delegation_hint": simple_delegation_hint,
        "enhance_delegation_hint": enhance_delegation_hint,
        "build_validator_roster": build_validator_roster,
        "process_validator_template": process_validator_template,
        "run_validator": run_validator,
    }

    for name, value in exported.items():
        assert callable(value), f"{name} should remain callable in edison.core.qa.validator"


@pytest.mark.parametrize(
    "module_name, expected_symbols",
    [
        (
            "edison.core.qa.validator.base",
            {
                "validate_dimension_weights",
                "process_validator_template",
                "run_validator",
                "_is_safe_path",
                "_resolve_include_path",
                "_read_text_safe",
            },
        ),
        (
            "edison.core.qa.validator.roster",
            {
                "build_validator_roster",
                "_detect_validators_from_git_diff",
                "_files_for_task",
                "_task_type_from_doc",
            },
        ),
        (
            "edison.core.qa.validator.delegation",
            {
                "simple_delegation_hint",
                "enhance_delegation_hint",
            },
        ),
    ],
)
def test_module_contains_expected_symbols(module_name: str, expected_symbols: set[str]) -> None:
    """Each split module should expose its responsibility-specific functions."""
    mod = importlib.import_module(module_name)
    for symbol in expected_symbols:
        assert hasattr(mod, symbol), f"{module_name} missing {symbol} after split"


def test_modules_import_independently_without_circular_dependencies() -> None:
    """Modules must import cleanly in any order, indicating no circular imports."""
    targets = [
        "edison.core.qa.validator.base",
        "edison.core.qa.validator.roster",
        "edison.core.qa.validator.delegation",
    ]

    for order in permutations(targets):
        for name in list(sys.modules):
            if name == "edison.core.qa.validator" or name.startswith("edison.core.qa.validator."):
                sys.modules.pop(name, None)

        for name in order:
            mod = importlib.import_module(name)
            assert mod is not None, f"Failed to import {name} in order {order}"


def test_split_modules_stay_under_loc_limits() -> None:
    """Each split module should remain lean (<200 LOC) to keep responsibilities focused."""
    repo_root = get_repo_root()
    validator_dir = repo_root / "src" / "edison" / "core" / "qa" / "validator"
    assert validator_dir.is_dir(), "validator directory should exist after split"

    loc_budget = 200
    files = [
        validator_dir / "__init__.py",
        validator_dir / "base.py",
        validator_dir / "roster.py",
        validator_dir / "delegation.py",
    ]

    for file_path in files:
        assert file_path.is_file(), f"Expected split module file missing: {file_path}"
        loc = len(file_path.read_text(encoding="utf-8").splitlines())
        assert (
            loc < loc_budget
        ), f"{file_path.name} too large after split ({loc} LOC, limit {loc_budget})"
