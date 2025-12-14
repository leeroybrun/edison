"""
Edison task claim command.

SUMMARY: Claim task or QA into a session with guarded status updates
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root, detect_record_type

SUMMARY = "Claim task or QA into a session with guarded status updates"


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
        "--reclaim",
        action="store_true",
        help="Allow reclaiming from another active session",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force claim even with warnings",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Claim task - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Lazy imports to keep CLI startup fast.
        from edison.core.task import TaskQAWorkflow, normalize_record_id
        from edison.core.session import lifecycle as session_manager
        from edison.core.session import validate_session_id
        from edison.core.config.domains.project import ProjectConfig
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.state.transitions import transition_entity, EntityTransitionError
        from edison.core.entity import PersistenceError, StateHistoryEntry
        from edison.core.qa.workflow.repository import QARepository

        # Determine record type (from arg or auto-detect)
        record_type = args.type or detect_record_type(args.record_id)

        # Normalize the record ID
        record_id = normalize_record_id(record_type, args.record_id)

        # Get or auto-detect session
        session_id = args.session
        if session_id:
            session_id = validate_session_id(session_id)
        else:
            # Try to get current session
            session_id = session_manager.get_current_session()

        if not session_id:
            raise ValueError("No session specified and no current session found. Use --session to specify one.")

        # Get owner
        owner = args.owner or ProjectConfig().get_owner_or_user()

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
            # Claim task using entity-based workflow
            task_entity = workflow.claim_task(record_id, session_id)

            # Optional post-claim transition to requested state
            if target_state != task_entity.state:
                if not args.force:
                    try:
                        transition_entity(
                            entity_type="task",
                            entity_id=record_id,
                            to_state=target_state,
                            current_state=task_entity.state,
                            context={
                                "task": task_entity.to_dict() if hasattr(task_entity, "to_dict") else {"id": record_id},
                                "session": {"id": session_id},
                                "session_id": session_id,
                            },
                            repo_root=project_root,
                        )
                    except EntityTransitionError as e:
                        raise PersistenceError(f"Transition blocked: {e}") from e

                old_state = task_entity.state
                task_entity.state = target_state
                task_entity.record_transition(old_state, target_state, reason="cli-claim-command")
                workflow.task_repo.save(task_entity)

            formatter.json_output({
                "status": "claimed",
                "record_id": record_id,
                "record_type": record_type,
                "session_id": session_id,
                "owner": owner,
                "state": task_entity.state,
            }) if formatter.json_mode else formatter.text(
                f"Claimed task {record_id}\n"
                f"Session: {session_id}\n"
                f"Owner: {owner}\n"
                f"Status: {task_entity.state}"
            )
        else:
            qa_repo = QARepository(project_root=project_root)
            qa = qa_repo.get(record_id)
            if not qa:
                raise ValueError(f"QA record not found: {record_id}")

            # Use transition_entity to validate guards and execute actions
            wip_state = workflow_cfg.get_semantic_state("qa", "wip")
            old_state = qa.state
            
            try:
                result = transition_entity(
                    entity_type="qa",
                    entity_id=record_id,
                    to_state=wip_state,
                    current_state=old_state,
                    context={
                        "qa": qa.to_dict() if hasattr(qa, 'to_dict') else {"id": qa.id},
                        "session": {"id": session_id},
                        "session_id": session_id,
                    },
                    repo_root=project_root,
                )
                
                # Update QA with transition result
                qa.state = result["state"]
                qa.session_id = session_id
                if "history_entry" in result:
                    entry = StateHistoryEntry.from_dict(result["history_entry"])
                    qa.state_history.append(entry)
                qa_repo.save(qa)
                
            except EntityTransitionError as e:
                raise ValueError(f"Cannot claim QA: {e}")

            # Optional post-claim transition to requested state
            if target_state != qa.state:
                if not args.force:
                    try:
                        result2 = transition_entity(
                            entity_type="qa",
                            entity_id=record_id,
                            to_state=target_state,
                            current_state=qa.state,
                            context={
                                "qa": qa.to_dict() if hasattr(qa, "to_dict") else {"id": qa.id},
                                "session": {"id": session_id},
                                "session_id": session_id,
                            },
                            repo_root=project_root,
                        )
                        if "history_entry" in result2:
                            qa.state_history.append(StateHistoryEntry.from_dict(result2["history_entry"]))
                    except EntityTransitionError as e:
                        raise PersistenceError(f"Transition blocked: {e}") from e

                old_state2 = qa.state
                qa.state = target_state
                qa.record_transition(old_state2, target_state, reason="cli-claim-command")
                qa_repo.save(qa)

            formatter.json_output({
                "status": "claimed",
                "record_id": record_id,
                "record_type": record_type,
                "session_id": session_id,
                "owner": owner,
                "state": qa.state,
            }) if formatter.json_mode else formatter.text(
                f"Claimed QA {record_id}\n"
                f"Session: {session_id}\n"
                f"Owner: {owner}\n"
                f"Status: {qa.state}"
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
