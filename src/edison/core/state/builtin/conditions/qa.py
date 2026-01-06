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
        from edison.core.qa.policy.resolver import ValidationPolicyResolver
        from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_status
        from edison.core.config.domains.qa import QAConfig

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
        required_files = [str(x).strip() for x in required if str(x).strip()]

        qa_cfg = QAConfig(repo_root=ev.project_root)
        evidence_files = (qa_cfg.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
        if not isinstance(evidence_files, dict):
            evidence_files = {}
        command_evidence_names = set(str(v).strip() for v in evidence_files.values() if str(v).strip())

        command_required = [f for f in required_files if f.startswith("command-") or f in command_evidence_names]
        round_required = [f for f in required_files if f not in command_required]

        # Round-scoped required evidence (reports/markers) lives under the task round dir.
        if round_required:
            from edison.core.qa.evidence.analysis import has_required_evidence as has_required_round

            if not has_required_round(round_dir, round_required):
                return False

        # Repo-scoped command evidence lives under the current fingerprint snapshot dir.
        if command_required:
            key = current_snapshot_key(project_root=ev.project_root)
            snap = snapshot_status(project_root=ev.project_root, key=key, required_files=command_required)
            if not (bool(snap.get("complete")) and bool(snap.get("valid")) and bool(snap.get("passed"))):
                return False

        return True

        # Bundle-aware fallback: allow the bundle root's evidence to satisfy the
        # per-task required evidence check when the member has an approved bundle
        # summary. This avoids requiring redundant command evidence on every
        # bundle member while remaining fail-closed when the root evidence is absent.
        try:
            bundle = ev.read_bundle()
            if isinstance(bundle, Mapping) and bundle.get("approved") is True:
                root_task = str(bundle.get("rootTask") or "").strip()
                if root_task and root_task != str(task_id) and bundle.get("scope"):
                    root_ev = EvidenceService(root_task, project_root=ev.project_root)
                    root_round = root_ev.get_current_round_dir()
                    if root_round is None:
                        return False

                    if round_required:
                        from edison.core.qa.evidence.analysis import has_required_evidence as has_required_round

                        if not has_required_round(root_round, round_required):
                            return False

                    if command_required:
                        key = current_snapshot_key(project_root=ev.project_root)
                        snap = snapshot_status(project_root=ev.project_root, key=key, required_files=command_required)
                        if not (bool(snap.get("complete")) and bool(snap.get("valid")) and bool(snap.get("passed"))):
                            return False

                    return True
        except Exception:
            pass

        return False
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
