"""QA-specific condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from edison.core.state.builtin.utils import get_task_id_from_context


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
        return False  # FAIL-CLOSED: cannot verify evidence without task context

    try:
        from edison.core.qa.evidence import EvidenceService
        from edison.core.qa.evidence.analysis import has_required_evidence as has_required
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        ev = EvidenceService(str(task_id))
        round_dir = ev.get_current_round_dir()
        if round_dir is None:
            return False

        session_obj = ctx.get("session")
        session_id = None
        if isinstance(session_obj, Mapping):
            session_id = session_obj.get("id")
        session_id = str(ctx.get("session_id") or session_id or "").strip() or None

        policy = ValidationPolicyResolver(project_root=ev.project_root).resolve_for_task(
            str(task_id),
            session_id=session_id,
        )
        required = list(policy.required_evidence or [])
        return has_required(round_dir, required)
    except Exception:
        return False  # FAIL-CLOSED


def has_bundle_approval(ctx: Mapping[str, Any]) -> bool:
    """Check if bundle approval exists.

    Args:
        ctx: Context with task_id

    Returns:
        True if bundle is approved
    """
    # Delegate to guard implementation
    from edison.core.state.builtin.guards.qa import has_bundle_approval as guard_check
    return guard_check(ctx)


def has_all_waves_passed(ctx: Mapping[str, Any]) -> bool:
    """Check if all validator waves have passed in order.

    Args:
        ctx: Context with task_id

    Returns:
        True if all waves passed
    """
    # Delegate to guard implementation
    from edison.core.state.builtin.guards.qa import has_all_waves_passed as guard_check
    return guard_check(ctx)


def all_blocking_validators_passed(ctx: Mapping[str, Any]) -> bool:
    """Check if all blocking validators passed.

    Args:
        ctx: Context with task_id or validation_results

    Returns:
        True if all blocking validators passed (verdict == "approve")
    """
    from edison.core.state.builtin.guards.qa import can_validate_qa

    # Delegate to the canonical FAIL-CLOSED implementation to avoid duplicated
    # evidence parsing and to enforce the current verdict vocabulary.
    return can_validate_qa(ctx)


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
        from edison.core.qa.evidence import read_validator_reports
        v = read_validator_reports(str(task_id))
        reports = v.get("reports", [])
        return len(reports) > 0
    except Exception:
        pass

    return False  # Fail-closed for this check


# Use shared utility for task_id extraction
_get_task_id = get_task_id_from_context
