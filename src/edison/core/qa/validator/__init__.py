"""Unified validator engine system.

This module provides the validator infrastructure for Edison's QA system.
The new engine-based architecture supports multiple execution backends
(CLI tools, delegation) with pluggable output parsers.

Usage:
    from edison.core.qa.validator import ValidationExecutor

    # Create executor for batch validation with wave support
    executor = ValidationExecutor(project_root=Path("/path/to/project"))
    result = executor.execute(
        task_id="T001",
        session_id="session-123",
        wave="critical",    # Optional: specific wave
        parallel=True,      # Run validators in parallel within waves
    )

    if result.all_blocking_passed:
        print("Validation passed!")

For single validator execution:
    from edison.core.qa.validator import EngineRegistry, ValidationResult

    registry = EngineRegistry(project_root=Path("/path/to/project"))
    result = registry.run_validator(
        validator_id="global-codex",
        task_id="T001",
        session_id="session-123",
        worktree_path=Path("/path/to/worktree"),
    )

For backward compatibility with template processing:
    from edison.core.qa.validator import process_validator_template, validate_dimension_weights
"""
from __future__ import annotations

from ...legacy_guard import enforce_no_legacy_project_root

enforce_no_legacy_project_root("lib.qa.validator")

# Keep utility functions from base.py
from .base import (
    _SAFE_INCLUDE_RE,
    _is_safe_path,
    _read_text_safe,
    _resolve_include_path,
    process_validator_template,
    run_validator,
    validate_dimension_weights,
)

# New engine-based API
from ..engines import (
    # Main API - Executor (preferred for batch execution)
    ValidationExecutor,
    ExecutionResult,
    WaveResult,
    # Registry for single validator execution
    EngineRegistry,
    ValidationResult,
    ValidatorConfig,
    EngineConfig,
    CLIEngine,
    ZenMCPEngine,
)

__all__ = [
    # Utility functions
    "validate_dimension_weights",
    "process_validator_template",
    "run_validator",
    # Engine-based API - Executor (preferred for batch execution)
    "ValidationExecutor",
    "ExecutionResult",
    "WaveResult",
    # Engine-based API - Registry (single validator)
    "EngineRegistry",
    "ValidationResult",
    "ValidatorConfig",
    "EngineConfig",
    "CLIEngine",
    "ZenMCPEngine",
]
