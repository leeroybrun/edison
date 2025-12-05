"""Unified validator engine system.

This module provides the core infrastructure for executing validators
across different execution backends (CLI tools, delegation, etc.).

Architecture:
    - ValidationExecutor: Main entry point for batch validation (preferred)
    - EngineRegistry: Lower-level registry for single validators
    - CLIEngine: Executes CLI-based validators (Codex, Claude, Gemini, etc.)
    - ZenMCPEngine: Generates delegation instructions for orchestrators
    - ValidationResult: Standard result format from all engines
    - ValidatorConfig: Configuration for individual validators
    - EngineConfig: Configuration for execution engines

Usage:
    from edison.core.qa.engines import ValidationExecutor

    # Create executor (centralized execution with wave support)
    executor = ValidationExecutor(project_root=Path("/path/to/project"))

    # Execute all validators for a task (with parallel execution per wave)
    result = executor.execute(
        task_id="T001",
        session_id="session-123",
        wave="critical",     # Optional: specific wave
        parallel=True,       # Run validators in parallel within waves
    )

    # Result contains wave-by-wave breakdown
    for wave in result.waves:
        print(f"Wave {wave.wave}: {len(wave.validators)} validators")

    # Check overall status
    if result.all_blocking_passed:
        print("Validation passed!")

For single validator execution:
    from edison.core.qa.engines import EngineRegistry

    registry = EngineRegistry(project_root=Path("/path/to/project"))
    result = registry.run_validator(
        validator_id="global-codex",
        task_id="T001",
        session_id="session-123",
        worktree_path=Path("/path/to/worktree"),
    )

Configuration:
    Engines and validators are configured in validators.yaml:

    validation:
      engines:
        codex-cli:
          type: cli
          command: "codex"
          response_parser: codex
        # ...

      validators:
        global-codex:
          engine: codex-cli
          fallback_engine: zen-mcp
          prompt: "_generated/validators/global.md"
          wave: critical
          always_run: true
        # ...

      waves:
        - name: critical
          validators: [global-codex, ...]
          execution: parallel
"""
from __future__ import annotations

from .base import EngineConfig, EngineProtocol, ValidationResult, ValidatorConfig
from .cli import CLIEngine
from .delegated import ZenMCPEngine
from .executor import ExecutionResult, ValidationExecutor, WaveResult
from .registry import EngineRegistry

__all__ = [
    # Main API - Executor (preferred for batch execution)
    "ValidationExecutor",
    "ExecutionResult",
    "WaveResult",
    # Main API - Registry (for single validator execution)
    "EngineRegistry",
    "ValidationResult",
    "ValidatorConfig",
    # Engine classes
    "CLIEngine",
    "ZenMCPEngine",
    # Configuration
    "EngineConfig",
    "EngineProtocol",
]

