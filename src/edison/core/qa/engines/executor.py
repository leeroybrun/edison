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
from datetime import datetime, timezone
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
    delegated_blocking: list[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Check if all validators in wave passed."""
        return all(v.verdict == "approve" for v in self.validators)

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
            if v.verdict == "approve"
        )

    @property
    def failed_count(self) -> int:
        """Count of failed validators."""
        return sum(
            1
            for w in self.waves
            for v in w.validators
            if v.verdict in ("reject", "blocked", "error")
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
                                "instructionsPath": task.get("instructionsPath"),
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
                extra_validators=extra_validators,
            )

            result.waves.append(wave_result)

            # Track overall blocking status
            if not wave_result.blocking_passed:
                result.all_blocking_passed = False
                result.blocking_failed.extend(wave_result.blocking_failed)

            # Track delegated validators
            result.delegated_validators.extend(wave_result.delegated_blocking)

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
        extra_validators: list[dict[str, str]] | None = None,
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
        #
        # IMPORTANT SEMANTICS:
        # - Waves define ORDER and execution behavior (parallel/sequential) via config.
        # - Validator membership in a wave is defined by `validator.wave`.
        # - Whether a validator should run for this task is determined by:
        #     - always_run == true  (always runs)
        #     - OR triggers match the task/session file context (pattern-triggered)
        # - Exception: if the caller explicitly requested specific validators, run only those (even if not triggered).
        registry = self._registry._validator_registry
        validators = registry.get_by_wave(wave)

        # If caller explicitly requested validators, honor that as an override.
        if validators_filter:
            validators = [v for v in validators if v.id in validators_filter]
        else:
            # Auto-trigger mode: run only always_run + triggered validators for this task.
            from edison.core.context.files import FileContextService

            file_ctx = FileContextService(project_root=self.project_root).get_for_task(
                task_id=task_id,
                session_id=session_id,
            )
            always_run, triggered_blocking, triggered_optional = registry.get_triggered_validators(
                files=file_ctx.all_files,
                wave=wave,
            )
            expected_ids = {v.id for v in (always_run + triggered_blocking + triggered_optional)}

            # Apply orchestrator-requested extra validators for this wave.
            if extra_validators:
                for ev in extra_validators:
                    if not isinstance(ev, dict):
                        continue
                    if str(ev.get("wave") or "") != str(wave):
                        continue
                    vid = ev.get("id")
                    if vid:
                        expected_ids.add(str(vid))

            validators = [v for v in validators if v.id in expected_ids]

        if blocking_only:
            validators = [v for v in validators if v.blocking]

        # Preserve the full set of validators for this wave (used for blocking checks),
        # even if we later skip execution due to existing reports.
        validators_in_wave = list(validators)

        # If there are no validators after filtering, return an empty wave result.
        if not validators_in_wave:
            logger.debug(f"No validators to run in wave '{wave}'")
            return WaveResult(wave=wave)

        # ---------------------------------------------------------------------
        # Reuse existing validator reports (do NOT re-run and overwrite them).
        #
        # This is critical for the "delegation" workflow:
        # - First run generates delegation instructions + pending reports.
        # - Orchestrator/validators write real `validator-*-report.md`.
        # - Re-running validation must detect those reports and treat them as complete.
        # ---------------------------------------------------------------------
        existing_results: list[ValidationResult] = []
        validators_to_run = []

        for vcfg in validators_in_wave:
            # If we don't have a round, we can't reuse per-round reports safely.
            if round_num is None:
                validators_to_run.append(vcfg)
                continue

            report = evidence_service.read_validator_report(vcfg.id, round_num=round_num) or {}
            try:
                if (
                    isinstance(report, dict)
                    and report.get("taskId") == task_id
                    and int(report.get("round") or 0) == int(round_num)
                    and (report.get("validatorId") == vcfg.id or report.get("validatorId") is None)
                    and isinstance(report.get("verdict"), str)
                    and report.get("verdict")
                ):
                    existing_results.append(
                        ValidationResult(
                            validator_id=vcfg.id,
                            verdict=str(report.get("verdict")),
                            summary=str(report.get("summary") or ""),
                            tracking=dict(report.get("tracking") or {}),
                        )
                    )
                    continue
            except Exception:
                # Fail closed into "execute" path when parsing is suspicious.
                pass

            validators_to_run.append(vcfg)

        # Separate by execution capability
        executable = []
        delegated = []

        from .cli import CLIEngine

        for config in validators_to_run:
            engine = self._registry._get_or_create_engine(config.engine)
            if isinstance(engine, CLIEngine) and engine.can_execute():
                executable.append(config)
            elif config.fallback_engine:
                fallback = self._registry._get_or_create_engine(config.fallback_engine)
                if isinstance(fallback, CLIEngine) and fallback.can_execute():
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
            delegated_blocking=[d.id for d in delegated if d.blocking],
        )
        wave_result.validators.extend(existing_results)

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
            self._persist_validator_report(
                validator=config,
                result=result,
                task_id=task_id,
                round_num=round_num,
                evidence_service=evidence_service,
            )

        # Check blocking status
        for config in validators_in_wave:
            if config.blocking:
                # Find result for this validator
                result = next(
                    (r for r in wave_result.validators if r.validator_id == config.id),
                    None,
                )
                # Blocking validators only "pass" when explicitly approved.
                #
                # Pending (delegated) validators are not failures, but they still
                # mean the blocking bar has NOT been met yet.
                if result is None or result.verdict != "approve":
                    wave_result.blocking_passed = False
                    if result is not None and result.verdict != "pending":
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
                    self._persist_validator_report(
                        validator=config,
                        result=result,
                        task_id=task_id,
                        round_num=round_num,
                        evidence_service=evidence_service,
                    )
                except Exception as e:
                    logger.error(f"Validator '{config.id}' failed: {e}")
                    err_result = ValidationResult(
                        validator_id=config.id,
                        verdict="error",
                        summary=f"Execution failed: {e}",
                        error=str(e),
                    )
                    results.append(err_result)
                    self._persist_validator_report(
                        validator=config,
                        result=err_result,
                        task_id=task_id,
                        round_num=round_num,
                        evidence_service=evidence_service,
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
                self._persist_validator_report(
                    validator=config,
                    result=result,
                    task_id=task_id,
                    round_num=round_num,
                    evidence_service=evidence_service,
                )
            except Exception as e:
                logger.error(f"Validator '{config.id}' failed: {e}")
                err_result = ValidationResult(
                    validator_id=config.id,
                    verdict="error",
                    summary=f"Execution failed: {e}",
                    error=str(e),
                )
                results.append(err_result)
                self._persist_validator_report(
                    validator=config,
                    result=err_result,
                    task_id=task_id,
                    round_num=round_num,
                    evidence_service=evidence_service,
                )

        return results

    def can_execute_validator(self, validator_id: str) -> bool:
        """Check if a validator can be executed directly via a CLI engine.

        Args:
            validator_id: Validator identifier

        Returns:
            True if CLI execution is available (not delegation fallback)
        """
        from .cli import CLIEngine

        config = self._registry.get_validator(validator_id)
        if not config:
            return False
        engine = self._registry._get_or_create_engine(config.engine)
        if isinstance(engine, CLIEngine) and engine.can_execute():
            return True
        if config.fallback_engine:
            fallback = self._registry._get_or_create_engine(config.fallback_engine)
            return isinstance(fallback, CLIEngine) and fallback.can_execute()
        return False

    # ------------------------------------------------------------------
    # Evidence persistence (validator reports)
    # ------------------------------------------------------------------

    def _persist_validator_report(
        self,
        *,
        validator: Any,
        result: ValidationResult,
        task_id: str,
        round_num: int | None,
        evidence_service: EvidenceService,
    ) -> None:
        """Write validator-<id>-report.md for executed validators.

        IMPORTANT:
        - We DO NOT write a report stub for delegated validators (they must be produced by the orchestrator/human).
        - We DO write reports for CLI-executed validators, even if verdict is "pending" or "blocked",
          so guards can reason over actual execution outcomes.
        """
        # Skip delegation-only results (those are instructions, not a validator report)
        for t in result.follow_up_tasks or []:
            if isinstance(t, dict) and t.get("type") == "delegation":
                return

        rn = round_num or evidence_service.get_current_round() or 1

        engine_id = str(getattr(validator, "engine", "") or "")
        model = self._infer_model_from_engine(engine_id)

        now = datetime.now(timezone.utc).isoformat()
        report = result.to_report(
            task_id=task_id,
            round_num=rn,
            model=model,
            zen_role=getattr(validator, "zen_role", None),
            started_at=now,
            completed_at=now,
        )
        evidence_service.write_validator_report(str(getattr(validator, "id", result.validator_id)), report, round_num=rn)

    @staticmethod
    def _infer_model_from_engine(engine_id: str) -> str:
        """Infer report.model from engine id.

        Schema treats this as an identifier; keep it stable and low-entropy.
        """
        e = (engine_id or "").lower()
        if "claude" in e:
            return "claude"
        if "codex" in e:
            return "codex"
        if "gemini" in e:
            return "gemini"
        if "auggie" in e:
            return "auggie"
        if "coderabbit" in e:
            return "coderabbit"
        return "unknown"

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
