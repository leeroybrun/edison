"""Task-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def can_start_task(ctx: Mapping[str, Any]) -> bool:
    """Task can start only if claimed by current session.

    FAIL-CLOSED: Returns False if any required data is missing.

    Prerequisites:
    - Task must exist in context
    - Session must exist in context
    - Task must be claimed by the session (matching session_id)

    Args:
        ctx: Context with 'task' and 'session' dicts

    Returns:
        True if task is claimed by current session
    """
    task = ctx.get("task")
    session = ctx.get("session")

    if not isinstance(task, Mapping) or not isinstance(session, Mapping):
        return False  # FAIL-CLOSED: missing context

    task_session = task.get("session_id") or task.get("sessionId")
    session_id = session.get("id")

    if not task_session or not session_id:
        return False  # FAIL-CLOSED: missing IDs

    return str(task_session) == str(session_id)


def can_finish_task(ctx: Mapping[str, Any]) -> bool:
    """Task can finish only when Context7 + evidence requirements are satisfied.

    FAIL-CLOSED: Returns False if evidence is missing.

    Prerequisites:
    - Task ID must be in context (via 'task.id' or 'entity_id')
    - Context7 markers must exist for any detected packages (react, zod, etc.)
    - Implementation report must exist for the latest round
    - If evidence enforcement is enabled, required evidence files must exist

    Args:
        ctx: Context with task ID (via 'task' dict or 'entity_id') and optionally 'project_root'

    Returns:
        True if requirements are satisfied
    """
    # Try to get task_id from various context patterns
    task_id = None

    # Pattern 1: task dict with id
    task = ctx.get("task")
    if isinstance(task, Mapping):
        task_id = task.get("id")

    # Pattern 2: entity_id (from transition_entity)
    if not task_id:
        task_id = ctx.get("entity_id")

    if not task_id:
        return False  # FAIL-CLOSED: no task ID found

    # Get project_root from context if available (for isolated test environments)
    project_root = ctx.get("project_root")
    project_root_path: Path | None = None
    if isinstance(project_root, (str, Path)):
        try:
            project_root_path = Path(project_root).resolve()
        except Exception:
            project_root_path = None

    # Context7 enforcement (must surface a useful error message).
    # Check if Context7 checks should be skipped (explicit bypass)
    skip_context7 = bool(ctx.get("skip_context7"))

    try:
        session = ctx.get("session")
        session_dict = session if isinstance(session, Mapping) else None

        from edison.core.qa.context import detect_packages, missing_packages_detailed
        from edison.core.task.repository import TaskRepository
        from edison.core.qa.evidence import EvidenceService

        task_repo = TaskRepository(project_root=project_root_path)
        task_path = task_repo._find_entity_path(str(task_id))
        if task_path and not skip_context7:
            packages = detect_packages(Path(task_path), session_dict)  # type: ignore[arg-type]
            detailed = missing_packages_detailed(str(task_id), packages)

            missing_pkgs = detailed.get("missing", [])
            invalid_markers = detailed.get("invalid", [])
            evidence_dir = detailed.get("evidence_dir")

            if missing_pkgs or invalid_markers:
                # Build a detailed, actionable error message
                lines: list[str] = ["Context7 evidence requirements not met:"]

                if evidence_dir:
                    lines.append(f"  Evidence directory: {evidence_dir}")

                if missing_pkgs:
                    lines.append(f"  Missing markers: {', '.join(missing_pkgs)}")

                if invalid_markers:
                    for inv in invalid_markers:
                        pkg = inv.get("package", "unknown")
                        missing_fields = inv.get("missing_fields", [])
                        lines.append(
                            f"  Invalid marker '{pkg}': missing required fields {missing_fields}"
                        )

                lines.append("")
                lines.append("To view current Context7 configuration:")
                lines.append("  edison config show context7 --format yaml")
                lines.append("")
                lines.append("To modify or disable Context7 requirements, edit:")
                lines.append("  .edison/config/context7.yaml")
                lines.append("")
                lines.append("To save Context7 evidence:")
                for pkg in missing_pkgs:
                    lines.append(
                        f"  edison evidence context7 save {task_id} {pkg} --library-id /<org>/{pkg} --topics <topics>"
                    )
                for inv in invalid_markers:
                    pkg = inv.get("package", "unknown")
                    lines.append(
                        f"  edison evidence context7 save {task_id} {pkg} --library-id /<org>/{pkg} --topics <topics>"
                    )

                raise ValueError("\n".join(lines))
    except ValueError:
        raise
    except Exception as e:
        # FAIL-CLOSED: if Context7 validation can't run reliably, block completion,
        # but do so with a clear, actionable error.
        raise ValueError(f"Context7 validation failed: {e}") from e

    # Check implementation report exists
    try:
        from edison.core.qa.evidence import EvidenceService

        ev_svc = EvidenceService(str(task_id), project_root=project_root_path)
        latest = ev_svc.get_current_round()
        if latest is None:
            expected = ev_svc.get_round_dir(1) / ev_svc.implementation_filename
            raise ValueError(
                "Implementation report Markdown is required per round (no round-* evidence directory found).\n"
                f"Expected: {expected}\n"
                "Fix: run `edison session track start --task <task> --type implementation` to create the round + report."
            )
        report = ev_svc.read_implementation_report(latest)
        if not report:
            expected = ev_svc.get_round_dir(latest) / ev_svc.implementation_filename
            raise ValueError(
                "Implementation report Markdown is required per round.\n"
                f"Missing: {expected}\n"
                "Fix: run `edison session track start --task <task> --type implementation --round <N>`."
            )

        enforce = bool(ctx.get("enforce_evidence")) or bool(
            os.environ.get("ENFORCE_TASK_STATUS_EVIDENCE")
        )
        if enforce:
            from edison.core.config.domains.qa import QAConfig
            from edison.core.tdd.ready_gate import (
                validate_command_evidence_exit_codes,
                format_evidence_error_message,
            )

            qa_config = QAConfig(repo_root=project_root_path)
            required = qa_config.get_required_evidence_files()
            round_dir = ev_svc.get_round_dir(latest)

            # Get CI commands for actionable error messages
            ci_commands: dict[str, str] = {}
            try:
                ci_section = qa_config.section.get("ci", {})
                if isinstance(ci_section, dict):
                    commands = ci_section.get("commands", {})
                    if isinstance(commands, dict):
                        ci_commands = {k: str(v) for k, v in commands.items() if v}
            except Exception:
                pass  # CI commands are optional for error messages

            # Validate command evidence exit codes (FAIL-CLOSED)
            errors = validate_command_evidence_exit_codes(
                round_dir, required, ci_commands
            )
            if errors:
                error_message = format_evidence_error_message(
                    task_id=str(task_id),
                    round_num=latest,
                    round_dir=round_dir,
                    errors=errors,
                    ci_commands=ci_commands,
                )
                raise ValueError(error_message)

        return True
    except Exception:
        raise

    return False  # pragma: no cover


def has_implementation_report(ctx: Mapping[str, Any]) -> bool:
    """Check if implementation report exists for the task.

    Alias for can_finish_task with clearer semantic meaning.

    Args:
        ctx: Context with 'task' dict containing 'id'

    Returns:
        True if implementation report exists
    """
    return can_finish_task(ctx)


def requires_rollback_reason(ctx: Mapping[str, Any]) -> bool:
    """Check if task has rollback reason for done->wip transition.

    FAIL-CLOSED: Returns False if rollback reason is missing.

    Args:
        ctx: Context with 'task' dict

    Returns:
        True if rollback reason is present
    """
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED

    reason = task.get("rollbackReason") or task.get("rollback_reason") or ""
    return bool(str(reason).strip())
