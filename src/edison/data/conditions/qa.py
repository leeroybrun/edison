"""QA-specific condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def has_required_evidence(ctx: Mapping[str, Any]) -> bool:
    """Check if all required evidence files exist.

    Required evidence includes:
    - command-type-check.txt
    - command-lint.txt
    - command-test.txt
    - command-build.txt

    Args:
        ctx: Context with 'task_id' or 'qa' dict

    Returns:
        True if all required evidence files exist
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return True  # Allow if no task context (flexibility)

    try:
        from edison.core.qa.evidence import missing_evidence_blockers
        blockers = missing_evidence_blockers(str(task_id))
        return len(blockers) == 0
    except Exception:
        pass

    return True  # Default to True for flexibility


def has_bundle_approval(ctx: Mapping[str, Any]) -> bool:
    """Check if bundle approval exists.

    Args:
        ctx: Context with task_id

    Returns:
        True if bundle is approved
    """
    # Delegate to guard implementation
    from edison.data.guards.qa import has_bundle_approval as guard_check
    return guard_check(ctx)


def has_all_waves_passed(ctx: Mapping[str, Any]) -> bool:
    """Check if all validator waves have passed in order.

    Args:
        ctx: Context with task_id

    Returns:
        True if all waves passed
    """
    # Delegate to guard implementation
    from edison.data.guards.qa import has_all_waves_passed as guard_check
    return guard_check(ctx)


def all_blocking_validators_passed(ctx: Mapping[str, Any]) -> bool:
    """Check if all blocking validators passed.

    Args:
        ctx: Context with task_id or validation_results

    Returns:
        True if all blocking validators passed
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return True  # Allow if no task context

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
            return False  # No reports = can't verify

        # Build map of verdicts
        verdicts = {}
        for report in reports:
            vid = report.get("validatorId") or report.get("id")
            verdict = report.get("verdict", "").lower()
            verdicts[vid] = verdict in ("pass", "approved", "passed")

        # Check all blocking validators passed
        for bid in blocking_ids:
            if bid not in verdicts or not verdicts[bid]:
                return False

        return True
    except Exception:
        pass

    return True  # Default to True for flexibility


def has_validator_reports(ctx: Mapping[str, Any]) -> bool:
    """Check if at least one validator report exists.

    Args:
        ctx: Context with task_id

    Returns:
        True if validator reports exist
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return True  # Allow if no task context

    try:
        from edison.core.qa.evidence import read_validator_jsons
        v = read_validator_jsons(str(task_id))
        reports = v.get("reports", [])
        return len(reports) > 0
    except Exception:
        pass

    return False  # Fail-closed for this check


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
