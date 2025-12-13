"""Validation executor for running validators.

This module provides the ValidationExecutor class which handles:
- Wave-based execution order
- Parallel execution within waves
- Mixed CLI and delegated validators
- Evidence collection and result aggregation

All validation execution logic is centralized here.
"""
from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import ValidationResult
from .registry import EngineRegistry

if TYPE_CHECKING:
    from edison.core.qa.evidence import EvidenceService

logger = logging.getLogger(__name__)


@dataclass
class WaveResult:
    """Result from executing a validation wave."""

    wave: str
    validators: list[ValidationResult] = field(default_factory=list)
    blocking_passed: bool = True
    blocking_failed: list[str] = field(default_factory=list)
    delegated: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Check if all validators in wave passed."""
        return all(
            v.verdict in ("approve", "approved", "pass", "passed")
            for v in self.validators
        )

    @property
    def has_delegated(self) -> bool:
        """Check if any validators were delegated."""
        return len(self.delegated) > 0


@dataclass
class ExecutionResult:
    """Result from full validation execution."""

    task_id: str
    session_id: str
    round_num: int | None
    waves: list[WaveResult] = field(default_factory=list)
    all_blocking_passed: bool = True
    blocking_failed: list[str] = field(default_factory=list)
    delegated_validators: list[str] = field(default_factory=list)

    @property
    def total_validators(self) -> int:
        """Total number of validators executed."""
        return sum(len(w.validators) for w in self.waves)

    @property
    def passed_count(self) -> int:
        """Count of passed validators."""
        return sum(
            1
            for w in self.waves
            for v in w.validators
            if v.verdict in ("approve", "approved", "pass", "passed")
        )

    @property
    def failed_count(self) -> int:
        """Count of failed validators."""
        return sum(
            1
            for w in self.waves
            for v in w.validators
            if v.verdict in ("reject", "rejected", "error")
        )

    @property
    def pending_count(self) -> int:
        """Count of pending validators (including delegated)."""
        return self.total_validators - self.passed_count - self.failed_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        # Collect delegation instructions from pending validators
        delegation_instructions: list[dict[str, Any]] = []
        for w in self.waves:
            for v in w.validators:
                if v.verdict == "pending" and v.follow_up_tasks:
                    for task in v.follow_up_tasks:
                        if task.get("type") == "delegation":
                            delegation_instructions.append({
                                "validator_id": v.validator_id,
                                "zen_role": task.get("zenRole"),
                                "instructions": task.get("instructions"),
                            })

        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "round": self.round_num,
            "waves": [
                {
                    "wave": w.wave,
                    "blocking_passed": w.blocking_passed,
                    "blocking_failed": w.blocking_failed,
                    "delegated": w.delegated,
                    "results": [
                        {
                            "validator_id": v.validator_id,
                            "verdict": v.verdict,
                            "duration": v.duration,
                            "exit_code": v.exit_code,
                            "error": v.error,
                            "follow_up_tasks": v.follow_up_tasks,
                        }
                        for v in w.validators
                    ],
                }
                for w in self.waves
            ],
            "summary": {
                "total": self.total_validators,
                "passed": self.passed_count,
                "failed": self.failed_count,
                "pending": self.pending_count,
            },
            "all_blocking_passed": self.all_blocking_passed,
            "blocking_failed": self.blocking_failed,
            "delegated_validators": self.delegated_validators,
            "delegation_instructions": delegation_instructions,
            "status": "completed" if not self.delegated_validators else "awaiting_delegation",
        }


class ValidationExecutor:
    """Centralized executor for validation operations.

    Handles wave-based execution with parallel validators within each wave.
    Supports mixed CLI and delegated validators.

    Example:
        executor = ValidationExecutor(project_root=Path("/path/to/project"))
        result = executor.execute(
            task_id="T001",
            session_id="session-123",
            wave="critical",  # Optional: run specific wave
            parallel=True,    # Run validators in parallel within waves
        )
    """

    def __init__(
        self,
        project_root: Path | None = None,
        max_workers: int = 4,
    ) -> None:
        """Initialize the validation executor.

        Args:
            project_root: Project root path
            max_workers: Maximum parallel workers for validator execution
        """
        self.project_root = project_root or Path.cwd()
        self.max_workers = max_workers
        self._registry = EngineRegistry(project_root=project_root)

    def execute(
        self,
        task_id: str,
        session_id: str,
        worktree_path: Path | None = None,
        wave: str | None = None,
        validators: list[str] | None = None,
        blocking_only: bool = False,
        parallel: bool = True,
        round_num: int | None = None,
        evidence_service: EvidenceService | None = None,
        extra_validators: list[dict[str, str]] | None = None,
    ) -> ExecutionResult:
        """Execute validators for a task.

        Args:
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree (default: project root)
            wave: Specific wave to run (default: all waves in order)
            validators: Specific validator IDs to run
            blocking_only: Only run blocking validators
            parallel: Run validators in parallel within waves
            round_num: Validation round number
            evidence_service: Evidence service for saving results
            extra_validators: Extra validators to add (from orchestrator)
                Each item: {"id": "validator-id", "wave": "wave-name"}

        Returns:
            ExecutionResult with all wave and validator results
        """
        worktree = worktree_path or self.project_root

        # Setup evidence service if not provided
        if evidence_service is None:
            from edison.core.qa.evidence import EvidenceService

            evidence_service = EvidenceService(task_id, project_root=self.project_root)

        # Ensure round exists
        if round_num is None:
            current = evidence_service.get_current_round()
            if current is None:
                evidence_service.create_next_round()
                round_num = evidence_service.get_current_round()
            else:
                round_num = current

        # Get waves to execute
        waves_to_run = self._get_waves_to_run(wave)

        # Execute each wave
        result = ExecutionResult(
            task_id=task_id,
            session_id=session_id,
            round_num=round_num,
        )

        for wave_name in waves_to_run:
            wave_result = self._execute_wave(
                wave=wave_name,
                task_id=task_id,
                session_id=session_id,
                worktree_path=worktree,
                validators_filter=validators,
                blocking_only=blocking_only,
                parallel=parallel,
                round_num=round_num,
                evidence_service=evidence_service,
            )

            result.waves.append(wave_result)

            # Track overall blocking status
            if not wave_result.blocking_passed:
                result.all_blocking_passed = False
                result.blocking_failed.extend(wave_result.blocking_failed)

            # Track delegated validators
            result.delegated_validators.extend(wave_result.delegated)

            # Stop on blocking failure if needed
            if not wave_result.blocking_passed:
                logger.warning(
                    f"Wave '{wave_name}' has blocking failures, "
                    f"stopping execution: {wave_result.blocking_failed}"
                )
                break

        return result

    def _get_waves_to_run(self, wave: str | None) -> list[str]:
        """Get ordered list of waves to execute.

        Args:
            wave: Specific wave name or None for all waves

        Returns:
            Ordered list of wave names
        """
        from edison.core.config.domains.qa import QAConfig

        qa_config = QAConfig(repo_root=self.project_root)
        waves_config = qa_config.get_waves()

        if wave:
            # Run specific wave only
            return [wave]

        # Get all waves in configured order
        return [w.get("name", "") for w in waves_config if w.get("name")]

    def _execute_wave(
        self,
        wave: str,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        validators_filter: list[str] | None,
        blocking_only: bool,
        parallel: bool,
        round_num: int | None,
        evidence_service: EvidenceService,
    ) -> WaveResult:
        """Execute all validators in a wave.

        Args:
            wave: Wave name
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree
            validators_filter: Optional filter for specific validators
            blocking_only: Only run blocking validators
            parallel: Run validators in parallel
            round_num: Validation round number
            evidence_service: Evidence service

        Returns:
            WaveResult with all validator results
        """
        logger.info(f"Executing wave '{wave}'")

        # Get validators for this wave using ValidatorRegistry (single source of truth)
        validators = self._registry._validator_registry.get_by_wave(wave)

        # Apply filters
        if validators_filter:
            validators = [v for v in validators if v.id in validators_filter]

        if blocking_only:
            validators = [v for v in validators if v.blocking]

        if not validators:
            logger.debug(f"No validators to run in wave '{wave}'")
            return WaveResult(wave=wave)

        # Separate by execution capability
        executable = []
        delegated = []

        for config in validators:
            engine = self._registry._get_or_create_engine(config.engine)
            if engine and engine.can_execute():
                executable.append(config)
            elif config.fallback_engine:
                fallback = self._registry._get_or_create_engine(config.fallback_engine)
                if fallback and fallback.can_execute():
                    executable.append(config)
                else:
                    delegated.append(config)
            else:
                delegated.append(config)

        logger.info(
            f"Wave '{wave}': {len(executable)} executable, {len(delegated)} delegated"
        )

        # Execute validators
        wave_result = WaveResult(
            wave=wave,
            delegated=[d.id for d in delegated],
        )

        # Run executable validators (parallel or sequential)
        if parallel and len(executable) > 1:
            results = self._execute_parallel(
                validators=executable,
                task_id=task_id,
                session_id=session_id,
                worktree_path=worktree_path,
                round_num=round_num,
                evidence_service=evidence_service,
            )
        else:
            results = self._execute_sequential(
                validators=executable,
                task_id=task_id,
                session_id=session_id,
                worktree_path=worktree_path,
                round_num=round_num,
                evidence_service=evidence_service,
            )

        wave_result.validators.extend(results)

        # Run delegated validators (always sequential, generates instructions)
        for config in delegated:
            result = self._registry.run_validator(
                validator_id=config.id,
                task_id=task_id,
                session_id=session_id,
                worktree_path=worktree_path,
                round_num=round_num,
                evidence_service=evidence_service,
            )
            wave_result.validators.append(result)

        # Check blocking status
        for config in validators:
            if config.blocking:
                # Find result for this validator
                result = next(
                    (r for r in wave_result.validators if r.validator_id == config.id),
                    None,
                )
                if result and result.verdict not in (
                    "approve",
                    "approved",
                    "pass",
                    "passed",
                    "pending",  # Delegated are pending, not failed
                ):
                    wave_result.blocking_passed = False
                    wave_result.blocking_failed.append(config.id)

        return wave_result

    def _execute_parallel(
        self,
        validators: list,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None,
        evidence_service: EvidenceService,
    ) -> list[ValidationResult]:
        """Execute validators in parallel.

        Args:
            validators: List of ValidatorConfig objects
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree
            round_num: Validation round number
            evidence_service: Evidence service

        Returns:
            List of ValidationResult objects
        """
        results = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = {
                executor.submit(
                    self._registry.run_validator,
                    validator_id=config.id,
                    task_id=task_id,
                    session_id=session_id,
                    worktree_path=worktree_path,
                    round_num=round_num,
                    evidence_service=evidence_service,
                ): config
                for config in validators
            }

            for future in concurrent.futures.as_completed(futures):
                config = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(
                        f"Validator '{config.id}' completed: {result.verdict}"
                    )
                except Exception as e:
                    logger.error(f"Validator '{config.id}' failed: {e}")
                    results.append(
                        ValidationResult(
                            validator_id=config.id,
                            verdict="error",
                            summary=f"Execution failed: {e}",
                            error=str(e),
                        )
                    )

        return results

    def _execute_sequential(
        self,
        validators: list,
        task_id: str,
        session_id: str,
        worktree_path: Path,
        round_num: int | None,
        evidence_service: EvidenceService,
    ) -> list[ValidationResult]:
        """Execute validators sequentially.

        Args:
            validators: List of ValidatorConfig objects
            task_id: Task identifier
            session_id: Session identifier
            worktree_path: Path to git worktree
            round_num: Validation round number
            evidence_service: Evidence service

        Returns:
            List of ValidationResult objects
        """
        results = []

        for config in validators:
            try:
                result = self._registry.run_validator(
                    validator_id=config.id,
                    task_id=task_id,
                    session_id=session_id,
                    worktree_path=worktree_path,
                    round_num=round_num,
                    evidence_service=evidence_service,
                )
                results.append(result)
                logger.info(f"Validator '{config.id}' completed: {result.verdict}")
            except Exception as e:
                logger.error(f"Validator '{config.id}' failed: {e}")
                results.append(
                    ValidationResult(
                        validator_id=config.id,
                        verdict="error",
                        summary=f"Execution failed: {e}",
                        error=str(e),
                    )
                )

        return results

    def can_execute_validator(self, validator_id: str) -> bool:
        """Check if a validator can be executed directly.

        Args:
            validator_id: Validator identifier

        Returns:
            True if CLI execution is available
        """
        config = self._registry.get_validator(validator_id)
        if not config:
            return False
        engine = self._registry._get_or_create_engine(config.engine)
        if engine and engine.can_execute():
            return True
        if config.fallback_engine:
            fallback = self._registry._get_or_create_engine(config.fallback_engine)
            return fallback is not None and fallback.can_execute()
        return False

    def get_registry(self) -> EngineRegistry:
        """Get the underlying engine registry."""
        return self._registry

    def get_validator_registry(self) -> "ValidatorRegistry":
        """Get the validator registry (single source of truth for validator data).

        Use this for build_execution_roster() and other validator metadata operations.
        """
        from edison.core.registries.validators import ValidatorRegistry
        return self._registry._validator_registry


__all__ = ["ValidationExecutor", "ExecutionResult", "WaveResult"]

