"""
Test that rules.py has been split into a rules/ package.

This test ensures the new package structure is in place and all
public symbols are still accessible via edison.core.rules imports.
"""
from __future__ import annotations

import pytest
from pathlib import Path


def test_rules_is_a_package():
    """Verify rules is now a package, not a single file."""
    from edison.core import rules

    # Should be a package (has __path__ attribute)
    assert hasattr(rules, '__path__'), "rules should be a package with __path__ attribute"

    # Verify the package directory exists
    package_path = Path(rules.__file__).parent
    assert package_path.name == 'rules', f"Expected 'rules' directory, got {package_path.name}"
    assert package_path.is_dir(), "rules should be a directory"


def test_rules_package_exports_registry_classes():
    """Verify RulesRegistry and compose_rules are exported from rules package."""
    from edison.core.rules import RulesRegistry, compose_rules

    # Should be able to import these classes
    assert RulesRegistry is not None
    assert compose_rules is not None
    assert callable(compose_rules)


def test_rules_package_exports_engine_classes():
    """Verify RulesEngine is exported from rules package."""
    from edison.core.rules import RulesEngine

    assert RulesEngine is not None


def test_rules_package_exports_model_classes():
    """Verify Rule and RuleViolation dataclasses are exported."""
    from edison.core.rules import Rule, RuleViolation

    assert Rule is not None
    assert RuleViolation is not None


def test_rules_package_exports_error_classes():
    """Verify RuleViolationError and other exceptions are exported."""
    from edison.core.rules import (
        RuleViolationError,
        AnchorNotFoundError,
        RulesCompositionError,
    )

    assert issubclass(RuleViolationError, Exception)
    assert issubclass(AnchorNotFoundError, KeyError)
    assert issubclass(RulesCompositionError, RuntimeError)


def test_rules_package_module_files_exist():
    """Verify all expected module files exist in the rules/ package.

    Note: registry.py, helpers.py, and file_patterns.py have been moved to
    composition/registries/ for architectural coherence. The rules package
    now only contains runtime enforcement components.
    """
    from edison.core import rules

    package_path = Path(rules.__file__).parent

    # Check all expected module files exist (runtime components only)
    expected_files = {
        '__init__.py',
        'engine.py',
        'models.py',
        'errors.py',
        'checkers.py',
    }

    existing_files = {f.name for f in package_path.iterdir() if f.is_file() and f.suffix == '.py'}

    missing = expected_files - existing_files
    assert not missing, f"Missing expected module files: {missing}"

    # Verify composition components are in their new location
    from edison.core.composition.registries import rules as rules_registry
    from edison.core.composition.registries import file_patterns as file_patterns_module
    assert rules_registry.RulesRegistry is not None
    assert rules_registry.compose_rules is not None
    assert file_patterns_module.FilePatternRegistry is not None


def test_no_legacy_rules_py_file():
    """Verify the old rules.py file has been deleted."""
    from edison.core import rules

    # Get the core directory
    core_path = Path(rules.__file__).parent.parent
    legacy_file = core_path / 'rules.py'

    assert not legacy_file.exists(), f"Legacy rules.py file should be deleted, found at {legacy_file}"


def test_module_files_under_500_loc():
    """Verify no module file exceeds 500 LOC limit."""
    from edison.core import rules

    package_path = Path(rules.__file__).parent

    for module_file in package_path.glob('*.py'):
        if module_file.name.startswith('__'):
            continue

        line_count = len(module_file.read_text().splitlines())
        assert line_count <= 500, (
            f"{module_file.name} has {line_count} lines, exceeds 500 LOC limit"
        )
