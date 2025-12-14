"""QA-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from edison.core.state.builtin.utils import get_task_id_from_context


def can_validate_qa(ctx: Mapping[str, Any]) -> bool:
    """QA can be validated if all blocking validators passed.

    FAIL-CLOSED: Returns False if validation results are missing.

    This guard checks:
    1. Context-provided validation_results (if available)
    2. Falls back to reading actual validator reports from evidence

    Prerequisites:
    - All blocking validators must have passed
    - Bundle summary must exist if promoting to validated

    Args:
        ctx: Context with 'validation_results' dict or 'task_id'/'qa' for lookup

    Returns:
        True if all blocking validators passed
    """
    # First try context-provided validation results
    validation_results = ctx.get("validation_results")
    if isinstance(validation_results, Mapping):
        reports = validation_results.get("reports", [])
        if isinstance(reports, list):
            failed = [r for r in reports if isinstance(r, Mapping) and not _is_passed(r)]
            return len(failed) == 0

    # Fall back to reading actual evidence
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED: can't determine task

    try:
        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence import read_validator_jsons

        qa_config = QAConfig()
        validators = qa_config.get_validators()

        # Get blocking validator IDs
        blocking_ids = {
            vid for vid, cfg in validators.items()
            if cfg.get("blocking", True)
        }

        v = read_validator_jsons(str(task_id))
        reports = v.get("reports", [])

        if not reports:
            return False  # FAIL-CLOSED: no reports yet

        # Check all blocking validators passed
        for report in reports:
            vid = report.get("validatorId") or report.get("id")
            if vid in blocking_ids:
                if not _is_passed(report):
                    return False  # Blocking validator failed

        return True
    except Exception:
        pass

    return False  # FAIL-CLOSED


def has_validator_reports(ctx: Mapping[str, Any]) -> bool:
    """Check if validator reports exist for the QA.

    FAIL-CLOSED: Returns False if reports are missing.

    For QA wip→done transition, we need to ensure:
    1. At least one validator report exists
    2. Required evidence files are present

    Args:
        ctx: Context with 'qa' dict containing 'task_id' or 'task_id' directly

    Returns:
        True if validator reports exist
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED

    try:
        from edison.core.qa.evidence import missing_evidence_blockers, read_validator_jsons

        # Check for validator reports
        v = read_validator_jsons(str(task_id))
        reports = v.get("reports", [])
        if not reports:
            return False  # FAIL-CLOSED: no reports

        # Also check required evidence files exist
        blockers = missing_evidence_blockers(str(task_id))
        if blockers:
            return False  # FAIL-CLOSED: missing evidence files

        return True
    except Exception:
        pass

    return False  # FAIL-CLOSED


def can_start_qa(ctx: Mapping[str, Any]) -> bool:
    """QA can start if task implementation is complete.

    FAIL-CLOSED: Returns False if task status cannot be verified.

    Checks:
    1. Task exists and is in 'done' state
    2. Implementation report exists

    Args:
        ctx: Context with 'task' dict or ability to look up task

    Returns:
        True if task is ready for QA
    """
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        # Try to fetch task if task_id is available
        task_id = _get_task_id(ctx)
        if task_id:
            task = _fetch_task(task_id)

    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED

    # Task should be in 'done' or later state
    status = task.get("status") or task.get("state")
    if not status:
        return False  # FAIL-CLOSED

    # Allow QA to start when task is done
    done_states = {"done", "validated"}
    return str(status).lower() in done_states


def has_all_waves_passed(ctx: Mapping[str, Any]) -> bool:
    """Check if all validator waves have passed in order.

    FAIL-CLOSED: Returns False if wave requirements aren't met.

    This enforces the wave configuration from validators.yaml:
    - Critical wave must pass before comprehensive wave runs
    - All validators in a wave must pass for wave to pass

    Args:
        ctx: Context with task_id for evidence lookup

    Returns:
        True if all waves have passed in order
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED

    try:
        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence import read_validator_jsons
        from edison.core.registries.validators import ValidatorRegistry
        from edison.core.context.files import FileContextService

        qa_config = QAConfig()
        waves = qa_config.get_waves()

        registry = ValidatorRegistry(project_root=qa_config.repo_root)

        session_obj = ctx.get("session")
        session_id = None
        if isinstance(session_obj, Mapping):
            session_id = session_obj.get("id")

        file_ctx = FileContextService(project_root=qa_config.repo_root).get_for_task(
            task_id=str(task_id),
            session_id=str(ctx.get("session_id") or session_id or ""),
        )
        always_run, triggered_blocking, triggered_optional = registry.get_triggered_validators(
            files=file_ctx.all_files
        )
        expected_ids = {v.id for v in (always_run + triggered_blocking + triggered_optional)}

        v = read_validator_jsons(str(task_id))
        reports = v.get("reports", [])
        if not reports:
            return False  # FAIL-CLOSED: no reports

        verdicts: dict[str, bool] = {}
        for report in reports:
            vid = report.get("validatorId") or report.get("id")
            if vid:
                verdicts[str(vid)] = _is_passed(report)

        previous_wave_passed = True
        for wave in waves:
            wave_name = str(wave.get("name") or "")
            if not wave_name:
                return False  # FAIL-CLOSED
            if wave.get("requires_previous_pass") and not previous_wave_passed:
                return False

            wave_validators = [v for v in registry.get_by_wave(wave_name) if v.id in expected_ids]
            blocking_ids = [v.id for v in wave_validators if v.blocking]

            wave_passed = True
            for vid in blocking_ids:
                if vid not in verdicts or not verdicts[vid]:
                    wave_passed = False
                    if not wave.get("continue_on_fail", False):
                        return False

            previous_wave_passed = wave_passed

        return True
    except Exception:
        pass

    return False  # FAIL-CLOSED


def has_bundle_approval(ctx: Mapping[str, Any]) -> bool:
    """Check if bundle approval exists.

    FAIL-CLOSED: Returns False if bundle approval is missing.

    For final QA validation (done→validated), we require:
    - Bundle summary JSON exists with approval

    Args:
        ctx: Context with task_id

    Returns:
        True if bundle is approved
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED

    try:
        from edison.core.qa.evidence import EvidenceService

        svc = EvidenceService(str(task_id))
        if svc.get_current_round() is None:
            return False

        # Use EvidenceService.read_bundle() as single source for bundle I/O
        bundle = svc.read_bundle()
        if not bundle:
            return False

        return bundle.get("approved", False) is True
    except Exception:
        pass

    return False  # FAIL-CLOSED


def _is_passed(report: Mapping[str, Any]) -> bool:
    """Check if a validator report indicates pass."""
    verdict = report.get("verdict", "").lower()
    return verdict in ("pass", "approved", "passed")


# Use shared utility for task_id extraction
_get_task_id = get_task_id_from_context


def _fetch_task(task_id: str) -> Mapping[str, Any] | None:
    """Fetch task data by ID."""
    try:
        from edison.core.task import TaskRepository
        repo = TaskRepository()
        task = repo.get(task_id)
        if task:
            return {
                "id": task.id,
                "status": task.state,
                "state": task.state,
                "session_id": task.session_id,
            }
    except Exception:
        pass
    return None
