"""
Edison task status command.

SUMMARY: Inspect or transition task/QA status with state-machine guards
"""

from __future__ import annotations

import argparse
import os
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    detect_record_type,
    format_display_path,
    get_repo_root,
    get_repository,
    resolve_existing_task_id,
    resolve_session_id,
)

SUMMARY = "Inspect or transition task/QA status with state-machine guards"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task or QA identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--status",
        help="Transition to this status (if omitted, shows current status)",
    )
    parser.add_argument(
        "--reason",
        help="Reason for transition (required for some guarded transitions like done→wip rollback)",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        help="Record type (auto-detects if not provided)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview transition without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force transition even when guards fail (bypasses validation/actions)",
    )
    parser.add_argument(
        "--session",
        help="Session context (enforces isolation when transitioning session-scoped records)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Task status - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Lazy imports to keep CLI startup fast.
        from edison.core.state.transitions import validate_transition
        from edison.core.task import normalize_record_id

        # Determine record type (from arg or auto-detect)
        record_type = args.type or detect_record_type(args.record_id)

        # SECURITY: prevent QA state transitions via tasks/status.
        #
        # tasks/status supports inspecting QA records for convenience, but all QA
        # transitions must be performed via the dedicated workflow command
        # `edison qa promote`, which enforces validation-first guards.
        if record_type == "qa" and args.status:
            raise ValueError(
                "QA state transitions must use edison qa promote (qa/promote), not tasks/status."
            )

        # Validate status against config-driven states (runtime validation for fast CLI startup)
        if args.status:
            from edison.core.config.domains.workflow import WorkflowConfig

            cfg = WorkflowConfig(repo_root=project_root)
            domain = record_type or "task"
            valid = cfg.get_states(domain)
            if args.status not in valid:
                raise ValueError(
                    f"Invalid status for {domain}: {args.status}. Valid values: {', '.join(valid)}"
                )

        # Normalize/resolve the record ID.
        # Tasks support shorthand resolution (e.g., "12007" -> "12007-wave8-...").
        if record_type == "task":
            record_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.record_id))
        else:
            record_id = normalize_record_id(record_type, args.record_id)

        # Get entity using repository
        repo = get_repository(record_type, project_root=project_root)

        entity = repo.get(record_id)
        if not entity:
            raise ValueError(f"{record_type.title()} not found: {record_id}")

        # Optional session scoping for security: prevent cross-session manipulation.
        session_id = None
        session_obj = None
        if getattr(args, "session", None):
            session_id = resolve_session_id(project_root=project_root, explicit=args.session, required=True)
            if getattr(entity, "session_id", None) and str(entity.session_id) != str(session_id):
                raise ValueError(f"Could not locate {record_type} {record_id} in session '{session_id}'")
            try:
                from edison.core.session.persistence.repository import SessionRepository

                sess = SessionRepository(project_root=project_root).get(session_id)
                session_obj = sess.to_dict() if sess else {"id": session_id}
            except Exception:
                session_obj = {"id": session_id}

        current_status = entity.state

        if args.status:
            # Transition to new status
            if args.dry_run:
                # Validate without executing
                context = {
                    "task": {
                        "id": entity.id,
                        "status": current_status,
                        "state": current_status,
                        "session_id": entity.session_id,
                    },
                    "task_id": entity.id,
                    "project_root": project_root,
                    "entity_type": record_type or "task",
                    "entity_id": entity.id,
                }
                if session_obj is not None:
                    context["session"] = session_obj
                    context["session_id"] = session_id
                if str(os.environ.get("ENFORCE_TASK_STATUS_EVIDENCE", "")).strip():
                    context["enforce_evidence"] = True
                if getattr(args, "reason", None):
                    context["task"]["rollback_reason"] = args.reason
                    context["task"]["rollbackReason"] = args.reason
                    context["task"]["blocker_reason"] = args.reason
                    context["task"]["blockerReason"] = args.reason

                is_valid, msg = validate_transition(
                    record_type or "task",
                    current_status,
                    args.status,
                    context=context,
                    repo_root=project_root,
                )
                if is_valid:
                    dry_run_text = f"Transition {current_status} -> {args.status}: ALLOWED"
                else:
                    dry_run_text = f"Transition {current_status} -> {args.status}: BLOCKED - {msg}"

                formatter.json_output({
                    "dry_run": True,
                    "record_id": record_id,
                    "current_status": current_status,
                    "target_status": args.status,
                    "force": bool(getattr(args, "force", False)),
                    "valid": is_valid,
                    "message": msg,
                }) if formatter.json_mode else formatter.text(dry_run_text)
                return 0 if is_valid else 1

            # Forced transition: bypass guards/conditions/actions, but still:
            # - enforce the target status is a configured state (validated above)
            # - record history + persist via repository
            if getattr(args, "force", False):
                old_state = entity.state
                try:
                    entity.record_transition(old_state, args.status, reason=args.reason or "cli-force")
                except Exception:
                    # FAIL-CLOSED is for guards, not for auditing; if record_transition fails,
                    # still proceed with the forced state update.
                    pass
                entity.state = args.status
                repo.save(entity)

                formatter.json_output({
                    "status": "transitioned",
                    "forced": True,
                    "record_id": record_id,
                    "from_status": current_status,
                    "to_status": args.status,
                }) if formatter.json_mode else formatter.text(
                    f"Forced transition {record_id}: {current_status} -> {args.status}"
                )
                return 0

            # Execute transition with guard enforcement + action execution.
            old_state = entity.state
            context = {
                "task": {
                    "id": entity.id,
                    "status": old_state,
                    "state": old_state,
                    "session_id": entity.session_id,
                },
                "task_id": entity.id,
                "project_root": project_root,
                "entity_type": record_type or "task",
                "entity_id": entity.id,
            }
            if session_obj is not None:
                context["session"] = session_obj
                context["session_id"] = session_id
            if str(os.environ.get("ENFORCE_TASK_STATUS_EVIDENCE", "")).strip():
                context["enforce_evidence"] = True
            if getattr(args, "reason", None):
                # Guards use snake_case and camelCase variants across call sites.
                context["task"]["rollback_reason"] = args.reason
                context["task"]["rollbackReason"] = args.reason
                context["task"]["blocker_reason"] = args.reason
                context["task"]["blockerReason"] = args.reason

            updated = repo.transition(
                entity.id,
                args.status,
                context=context,
                reason=args.reason or "cli-status-command",
            )

            # Best-effort: when a task reaches "done", the associated QA should become
            # ready for validation (waiting -> todo).
            if record_type != "qa":
                try:
                    from edison.core.config.domains.workflow import WorkflowConfig
                    from edison.core.qa.workflow.repository import QARepository

                    cfg = WorkflowConfig(repo_root=project_root)
                    done_state = cfg.get_semantic_state("task", "done")
                    if str(args.status) == str(done_state):
                        qa_repo = QARepository(project_root=project_root)
                        qa_id = f"{updated.id}-qa"
                        qa = qa_repo.get(qa_id)
                        if qa:
                            waiting = cfg.get_semantic_state("qa", "waiting")
                            todo = cfg.get_semantic_state("qa", "todo")
                            if str(qa.state) == str(waiting):
                                qa_repo.advance_state(
                                    qa_id,
                                    todo,
                                    session_id=str(getattr(updated, "session_id", None) or session_id or ""),
                                )
                except Exception:
                    pass

            # Best-effort: keep session index up-to-date for task transitions.
            if record_type != "qa" and getattr(updated, "session_id", None):
                try:
                    from edison.core.session.persistence.graph import register_task

                    register_task(
                        str(updated.session_id),
                        str(updated.id),
                        owner=(updated.metadata.created_by or "_unassigned_") if getattr(updated, "metadata", None) else "_unassigned_",
                        status=str(updated.state),
                    )
                except Exception:
                    pass

            formatter.json_output({
                "status": "transitioned",
                "forced": False,
                "record_id": record_id,
                "from_status": current_status,
                "to_status": args.status,
            }) if formatter.json_mode else formatter.text(
                f"Status transitioned {record_id}: {current_status} -> {args.status}"
            )

        else:
            # Show current status
            path_display = ""
            evidence_root_display = ""
            try:
                entity_path = repo.get_path(entity.id)
                path_display = format_display_path(project_root=project_root, path=entity_path)
            except Exception:
                path_display = ""

            try:
                from edison.core.qa.evidence import EvidenceService

                evidence_task_id = ""
                if record_type == "task":
                    evidence_task_id = str(entity.id)
                elif record_type == "qa":
                    evidence_task_id = str(getattr(entity, "task_id", "") or "").strip()

                if evidence_task_id:
                    evidence_root = EvidenceService(evidence_task_id, project_root=project_root).get_evidence_root()
                    evidence_root_display = format_display_path(project_root=project_root, path=evidence_root)
            except Exception:
                evidence_root_display = ""

            status_text = f"Task: {record_id}\n"
            status_text += f"Type: {record_type or 'task'}\n"
            status_text += f"Status: {entity.state}"
            if hasattr(entity, "title") and entity.title:
                status_text += f"\nTitle: {entity.title}"
            if entity.session_id:
                status_text += f"\nSession: {entity.session_id}"
            if path_display:
                status_text += f"\nPath: {path_display}"
            if evidence_root_display:
                status_text += f"\nEvidence: {evidence_root_display}"

            formatter.json_output({
                "record_id": record_id,
                "record_type": record_type,
                "status": entity.state,
                "title": getattr(entity, "title", ""),
                "session_id": entity.session_id,
                "path": path_display,
                "evidenceRoot": evidence_root_display,
                "metadata": {
                    "created_by": entity.metadata.created_by if entity.metadata else None,
                    "created_at": str(entity.metadata.created_at) if entity.metadata else None,
                },
            }) if formatter.json_mode else formatter.text(status_text)

        return 0

    except Exception as e:
        formatter.error(e, error_code="status_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
