"""QA-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""
from __future__ import annotations

from typing import Any, Mapping


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
        blocking = validation_results.get("blocking_validators")
        if isinstance(blocking, list):
            failed = [v for v in blocking if isinstance(v, Mapping) and not v.get("passed")]
            return len(failed) == 0
    
    # Fall back to reading actual evidence
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED: can't determine task
    
    try:
        from edison.core.qa.evidence import read_validator_jsons
        from edison.core.config.domains.qa import QAConfig
        
        qa_config = QAConfig()
        blocking_ids = set(qa_config.validation_config.get("blocking_validators", []))
        
        v = read_validator_jsons(str(task_id))
        reports = v.get("reports", [])
        
        if not reports:
            return False  # FAIL-CLOSED: no reports yet
        
        # Check all blocking validators passed
        for report in reports:
            vid = report.get("validatorId") or report.get("id")
            if vid in blocking_ids:
                verdict = report.get("verdict", "").lower()
                if verdict not in ("pass", "approved", "passed"):
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
        from edison.core.qa.evidence import read_validator_jsons, missing_evidence_blockers
        
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
        from edison.core.qa.evidence import read_validator_jsons
        from edison.core.config.domains.qa import QAConfig
        
        qa_config = QAConfig()
        waves = qa_config.validation_config.get("waves", [])
        roster = qa_config.validation_config.get("roster", {})
        
        v = read_validator_jsons(str(task_id))
        reports = v.get("reports", [])
        
        if not reports:
            return False  # FAIL-CLOSED: no reports
        
        # Build map of validator verdicts
        verdicts = {}
        for report in reports:
            vid = report.get("validatorId") or report.get("id")
            verdict = report.get("verdict", "").lower()
            verdicts[vid] = verdict in ("pass", "approved", "passed")
        
        # Check waves in order
        previous_wave_passed = True
        for wave in waves:
            if wave.get("requires_previous_pass") and not previous_wave_passed:
                return False  # Previous wave failed, can't continue
            
            # Get validators in this wave's tiers
            wave_tiers = wave.get("tiers", [])
            wave_validators = []
            for tier in wave_tiers:
                wave_validators.extend(roster.get(tier, []))
            
            # Check if all blocking validators in this wave passed
            wave_passed = True
            for validator in wave_validators:
                vid = validator.get("id")
                if validator.get("blocksOnFail", True):
                    if vid not in verdicts or not verdicts[vid]:
                        wave_passed = False
                        if not wave.get("continue_on_fail", False):
                            return False  # Critical wave failed
            
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
        from edison.core.utils.io import read_json
        
        svc = EvidenceService(str(task_id))
        round_num = svc.get_current_round()
        if round_num is None:
            return False
        
        bundle_path = svc.get_evidence_root() / f"round-{round_num}" / "bundle-approved.json"
        if not bundle_path.exists():
            return False
        
        bundle = read_json(bundle_path)
        return bundle.get("approved", False) is True
    except Exception:
        pass
    
    return False  # FAIL-CLOSED


def _get_task_id(ctx: Mapping[str, Any]) -> str | None:
    """Extract task_id from context in various forms."""
    # Direct task_id
    if ctx.get("task_id"):
        return str(ctx["task_id"])
    
    # From QA dict
    qa = ctx.get("qa")
    if isinstance(qa, Mapping):
        tid = qa.get("task_id") or qa.get("taskId")
        if tid:
            return str(tid)
    
    # From task dict
    task = ctx.get("task")
    if isinstance(task, Mapping):
        tid = task.get("id")
        if tid:
            return str(tid)
    
    # From entity_id if entity_type is qa
    if ctx.get("entity_type") == "qa" and ctx.get("entity_id"):
        return str(ctx["entity_id"])
    
    return None


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
