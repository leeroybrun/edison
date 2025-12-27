"""Tests for the unified validator engine system architecture.

Tests that the new engine-based validator system is properly structured
with clean imports and appropriate module organization.
"""
from __future__ import annotations

import importlib
import sys
from itertools import permutations
from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root


def test_engine_api_imports() -> None:
    """Public API should expose the new engine-based validator system."""
    from edison.core.qa.validator import (
        validate_dimension_weights,
        process_validator_template,
        run_validator,
        EngineRegistry,
        ValidationResult,
        CLIEngine,
        PalMCPEngine,
    )
    # ValidatorMetadata is now in registries module
    from edison.core.registries.validators import ValidatorMetadata

    exported = {
        "validate_dimension_weights": validate_dimension_weights,
        "process_validator_template": process_validator_template,
        "run_validator": run_validator,
        "EngineRegistry": EngineRegistry,
        "ValidationResult": ValidationResult,
        "ValidatorMetadata": ValidatorMetadata,
        "CLIEngine": CLIEngine,
        "PalMCPEngine": PalMCPEngine,
    }

    for name, value in exported.items():
        assert value is not None, f"{name} should be exported from appropriate module"


def test_engines_module_structure() -> None:
    """The engines module should have the expected structure."""
    from edison.core.qa import engines

    # Check main exports (ValidatorConfig moved to registries as ValidatorMetadata)
    assert hasattr(engines, "EngineRegistry")
    assert hasattr(engines, "ValidationResult")
    assert hasattr(engines, "EngineConfig")
    assert hasattr(engines, "CLIEngine")
    assert hasattr(engines, "PalMCPEngine")


def test_parsers_module_structure() -> None:
    """The parsers module should have the expected structure."""
    from edison.core.qa.engines import parsers

    # Check parser API
    assert hasattr(parsers, "get_parser")
    assert hasattr(parsers, "load_parsers")
    assert hasattr(parsers, "ParseResult")


@pytest.mark.parametrize(
    "module_name, expected_symbols",
    [
        (
            "edison.core.qa.engines.base",
            {
                "ValidationResult",
                "EngineConfig",
                "EngineProtocol",
            },
        ),
        (
            "edison.core.qa.engines.cli",
            {
                "CLIEngine",
            },
        ),
        (
            "edison.core.qa.engines.delegated",
            {
                "PalMCPEngine",
            },
        ),
        (
            "edison.core.qa.engines.registry",
            {
                "EngineRegistry",
            },
        ),
        (
            "edison.core.registries.validators",
            {
                "ValidatorRegistry",
                "ValidatorMetadata",
            },
        ),
    ],
)
def test_engine_module_contains_expected_symbols(module_name: str, expected_symbols: set[str]) -> None:
    """Each engine module should expose its responsibility-specific classes."""
    mod = importlib.import_module(module_name)
    for symbol in expected_symbols:
        assert hasattr(mod, symbol), f"{module_name} missing {symbol}"


def test_engine_modules_import_independently() -> None:
    """Engine modules must import cleanly in any order."""
    targets = [
        "edison.core.qa.engines.base",
        "edison.core.qa.engines.cli",
        "edison.core.qa.engines.delegated",
        "edison.core.qa.engines.registry",
    ]

    for order in permutations(targets):
        for name in list(sys.modules):
            if name == "edison.core.qa.engines" or name.startswith("edison.core.qa.engines."):
                sys.modules.pop(name, None)

        for name in order:
            mod = importlib.import_module(name)
            assert mod is not None, f"Failed to import {name} in order {order}"


def test_parser_files_exist() -> None:
    """Core parser files should exist."""
    repo_root = get_repo_root()
    parsers_dir = repo_root / "src" / "edison" / "core" / "qa" / "engines" / "parsers"
    assert parsers_dir.is_dir(), "parsers directory should exist"

    expected_parsers = [
        "codex.py",
        "claude.py",
        "gemini.py",
        "auggie.py",
        "coderabbit.py",
        "plain_text.py",
    ]

    for parser_file in expected_parsers:
        parser_path = parsers_dir / parser_file
        assert parser_path.is_file(), f"Expected parser file missing: {parser_file}"


def test_parsers_have_parse_function() -> None:
    """Each parser module should export a parse() function."""
    parser_modules = [
        "edison.core.qa.engines.parsers.codex",
        "edison.core.qa.engines.parsers.claude",
        "edison.core.qa.engines.parsers.gemini",
        "edison.core.qa.engines.parsers.auggie",
        "edison.core.qa.engines.parsers.coderabbit",
        "edison.core.qa.engines.parsers.plain_text",
    ]

    for module_name in parser_modules:
        mod = importlib.import_module(module_name)
        assert hasattr(mod, "parse"), f"{module_name} should export parse()"
        assert callable(mod.parse), f"{module_name}.parse should be callable"
