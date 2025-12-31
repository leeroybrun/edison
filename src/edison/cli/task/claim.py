"""
Edison task claim command.

SUMMARY: Claim task or QA into a session with guarded status updates
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    detect_record_type,
    get_repo_root,
    resolve_session_id,
)

SUMMARY = "Claim task or QA into a session with guarded status updates"

def _is_truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _detect_strict_guard_wrappers(project_root: Path) -> bool:
    scripts_dir = project_root / "scripts"
    return (
        (scripts_dir / "implementation" / "validate").exists()
        and (scripts_dir / "tasks" / "ensure-followups").exists()
    )


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task or QA identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--session",
        help="Session to claim into (auto-detects if not provided)",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        help="Record type (auto-detects if not provided)",
    )
    parser.add_argument(
        "--owner",
        help="Owner name to stamp (defaults to git user or system user)",
    )
    parser.add_argument(
        "--status",
        type=str,
        default=None,
        help="Target status after claim (default: semantic wip). Validated against config at runtime.",
    )
    parser.add_argument(
        "--takeover",
        action="store_true",
        help="Allow taking over a task already claimed by another (inactive/expired) session (tasks only).",
    )
    parser.add_argument(
        "--reason",
        type=str,
        default=None,
        help="Reason for takeover (required with --takeover).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Claim task - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)
        strict_wrappers = _detect_strict_guard_wrappers(project_root)
        debug_wrappers = _is_truthy_env("project_DEBUG_WRAPPERS")

        # Lazy imports to keep CLI startup fast.
        from edison.core.config.domains.project import ProjectConfig
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.qa.workflow.repository import QARepository
        from edison.core.task import TaskQAWorkflow, normalize_record_id

        # Determine record type (from arg or auto-detect)
        record_type = args.type or detect_record_type(args.record_id)

        # Normalize the record ID
        record_id = normalize_record_id(record_type, args.record_id)

        # Get or auto-detect session
        session_id = resolve_session_id(
            project_root=project_root,
            explicit=args.session,
            required=True,
        )
        assert session_id is not None

        # Get owner (for stamping when missing)
        owner = args.owner or ProjectConfig(repo_root=project_root).get_owner_or_user()

        # Use TaskQAWorkflow for claiming (handles state transition and persistence)
        workflow = TaskQAWorkflow(project_root=project_root)

        workflow_cfg = WorkflowConfig(repo_root=project_root)
        domain = "qa" if record_type == "qa" else "task"
        default_state = workflow_cfg.get_semantic_state(domain, "wip")
        target_state = str(args.status).strip() if args.status else default_state

        valid_states = workflow_cfg.get_states(domain)
        if target_state not in valid_states:
            raise ValueError(
                f"Invalid status for {domain}: {target_state}. Valid values: {', '.join(valid_states)}"
            )

        if record_type == "task":
            if bool(getattr(args, "takeover", False)) and not (str(getattr(args, "reason", "") or "").strip()):
                raise ValueError("--takeover requires --reason")

            # Claim task using entity-based workflow
            task_entity = workflow.claim_task(
                record_id,
                session_id,
                owner=owner,
                takeover=bool(getattr(args, "takeover", False)),
                takeover_reason=str(getattr(args, "reason", "") or "").strip() or None,
            )

            # Optional post-claim transition to requested state
            if target_state != task_entity.state:
                task_entity = workflow.task_repo.transition(
                    task_entity.id,
                    target_state,
                    context={
                        "task": task_entity.to_dict(),
                        "session": {"id": session_id},
                        "session_id": session_id,
                        "entity_type": "task",
                        "entity_id": task_entity.id,
                    },
                    reason="cli-claim-command",
                )

            effective_owner = (task_entity.metadata.created_by or owner or "").strip() or "_unassigned_"

            formatter.json_output({
                "status": "claimed",
                "record_id": record_id,
                "record_type": record_type,
                "session_id": session_id,
                "owner": effective_owner,
                "state": task_entity.state,
                "strict_wrappers": strict_wrappers,
            }) if formatter.json_mode else formatter.text(
                f"Claimed task {record_id}\n"
                f"Session: {session_id}\n"
                f"Owner: {effective_owner}\n"
                f"Status: {task_entity.state}"
                + (f"\nStrict Wrappers → {'yes' if strict_wrappers else 'no'}" if debug_wrappers else "")
            )
        else:
            qa_repo = QARepository(project_root=project_root)
            qa = qa_repo.get(record_id)
            if not qa:
                raise ValueError(f"QA record not found: {record_id}")

            # Transition QA into semantic wip on claim.
            wip_state = workflow_cfg.get_semantic_state("qa", "wip")

            def _mutate_claimed(q: Any) -> None:
                q.session_id = session_id
                if owner and not (getattr(q, "validator_owner", "") or "").strip():
                    q.validator_owner = owner
                if owner and not (getattr(getattr(q, "metadata", None), "created_by", "") or "").strip():
                    q.metadata.created_by = owner

            qa = qa_repo.transition(
                record_id,
                wip_state,
                context={
                    "qa": qa.to_dict(),
                    "session": {"id": session_id},
                    "session_id": session_id,
                    "entity_type": "qa",
                    "entity_id": record_id,
                },
                reason="cli-claim-command",
                mutate=_mutate_claimed,
            )

            # Optional post-claim transition to requested state
            if target_state != qa.state:
                qa = qa_repo.transition(
                    record_id,
                    target_state,
                    context={
                        "qa": qa.to_dict(),
                        "session": {"id": session_id},
                        "session_id": session_id,
                        "entity_type": "qa",
                        "entity_id": record_id,
                    },
                    reason="cli-claim-command",
                    mutate=_mutate_claimed,
                )

            effective_owner = (getattr(qa, "validator_owner", None) or getattr(getattr(qa, "metadata", None), "created_by", None) or owner or "").strip() or "_unassigned_"

            formatter.json_output({
                "status": "claimed",
                "record_id": record_id,
                "record_type": record_type,
                "session_id": session_id,
                "owner": effective_owner,
                "state": qa.state,
                "strict_wrappers": strict_wrappers,
            }) if formatter.json_mode else formatter.text(
                f"Claimed QA {record_id}\n"
                f"Session: {session_id}\n"
                f"Owner: {effective_owner}\n"
                f"Status: {qa.state}"
                + (f"\nStrict Wrappers → {'yes' if strict_wrappers else 'no'}" if debug_wrappers else "")
            )

        return 0

    except Exception as e:
        formatter.error(e, error_code="claim_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
