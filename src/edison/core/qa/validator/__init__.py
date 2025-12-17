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

"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from ...legacy_guard import enforce_no_legacy_project_root

enforce_no_legacy_project_root("lib.qa.validator")

# New engine-based API
from ..engines import (
    # Main API - Executor (preferred for batch execution)
    ValidationExecutor,
    ExecutionResult,
    WaveResult,
    # Registry for single validator execution
    EngineRegistry,
    ValidationResult,
    EngineConfig,
    CLIEngine,
    ZenMCPEngine,
)

# ---------------------------------------------------------------------------
# Backwards-compatible functional API
# ---------------------------------------------------------------------------

def validate_dimension_weights(dimensions: Mapping[str, Any]) -> None:
    """Validate that a dimension-weight mapping is non-empty and has positive total weight."""
    if not dimensions:
        raise ValueError("dimensions mapping must not be empty")
    total = 0
    for v in dimensions.values():
        try:
            total += int(v)
        except Exception as e:
            raise ValueError(f"dimension weight must be an integer: {v!r}") from e
    if total <= 0:
        raise ValueError("dimension weights must sum to a positive value")


def process_validator_template(
    name: str,
    *,
    packs: Optional[list[str]] = None,
    project_root: Optional[Path] = None,
) -> str:
    """Compose and return a validator prompt template by name."""
    from edison.core.composition.registries.validator_prompts import ValidatorPromptRegistry

    reg = ValidatorPromptRegistry(project_root=project_root)
    composed = reg.compose(name, packs=packs)
    if composed is None:
        raise ValueError(f"Validator template '{name}' not found")
    return composed


def run_validator(
    validator_id: str,
    task_id: str,
    session_id: str,
    worktree_path: Path,
    *,
    round_num: int | None = None,
    project_root: Optional[Path] = None,
) -> ValidationResult:
    """Convenience wrapper around EngineRegistry.run_validator()."""
    return EngineRegistry(project_root=project_root).run_validator(
        validator_id=validator_id,
        task_id=task_id,
        session_id=session_id,
        worktree_path=worktree_path,
        round_num=round_num,
    )

# ValidatorMetadata is now in registries module
# Import for backward compatibility if needed:
# from edison.core.registries.validators import ValidatorMetadata

__all__ = [
    # Engine-based API - Executor (preferred for batch execution)
    "ValidationExecutor",
    "ExecutionResult",
    "WaveResult",
    # Engine-based API - Registry (single validator)
    "EngineRegistry",
    "ValidationResult",
    "EngineConfig",
    "CLIEngine",
    "ZenMCPEngine",
    # Backwards-compatible functional API
    "validate_dimension_weights",
    "process_validator_template",
    "run_validator",
]
