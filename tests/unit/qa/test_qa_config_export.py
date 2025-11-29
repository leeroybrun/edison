"""Test that QA config is properly exported from edison.core.qa package.

This ensures backward compatibility after the config refactoring.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_config_module_exported_from_qa_package() -> None:
    """The config module should be importable from edison.core.qa."""
    from edison.core.qa import config  # type: ignore[attr-defined]

    # Should have the expected functions
    assert hasattr(config, "load_config")
    assert hasattr(config, "load_delegation_config")
    assert hasattr(config, "load_validation_config")
    assert hasattr(config, "max_concurrent_validators")

    # Should have the QAConfig class
    assert hasattr(config, "QAConfig")


def test_config_functions_work_correctly(tmp_path: Path) -> None:
    """Config functions imported from edison.core.qa should work correctly."""
    from edison.core.qa import config  # type: ignore[attr-defined]

    # These should not raise errors (will use defaults)
    delegation = config.load_delegation_config()
    validation = config.load_validation_config()

    assert isinstance(delegation, dict)
    assert isinstance(validation, dict)


def test_qa_config_class_works(tmp_path: Path) -> None:
    """QAConfig class imported from edison.core.qa should work correctly."""
    from edison.core.qa import config  # type: ignore[attr-defined]

    qa_config = config.QAConfig()

    # Should have the expected properties
    assert hasattr(qa_config, "delegation_config")
    assert hasattr(qa_config, "validation_config")
    assert hasattr(qa_config, "get_delegation_config")
    assert hasattr(qa_config, "get_validation_config")
    assert hasattr(qa_config, "get_required_evidence_files")
    assert hasattr(qa_config, "get_max_concurrent_validators")
