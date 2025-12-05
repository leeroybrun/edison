"""
Edison task status command.

SUMMARY: Inspect or transition task/QA status with state-machine guards
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root, detect_record_type, get_repository
from edison.cli._choices import get_combined_state_choices
from edison.core.task import normalize_record_id
from edison.core.state.transitions import validate_transition, transition_entity, EntityTransitionError

SUMMARY = "Inspect or transition task/QA status with state-machine guards"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task or QA identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--status",
        choices=get_combined_state_choices(),
        help="Transition to this status (if omitted, shows current status)",
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
        help="Force transition even when guards fail",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Task status - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Determine record type (from arg or auto-detect)
        record_type = args.type or detect_record_type(args.record_id)

        # Normalize the record ID
        record_id = normalize_record_id(record_type, args.record_id)

        # Get entity using repository
        repo = get_repository(record_type, project_root=project_root)

        entity = repo.get(record_id)
        if not entity:
            raise ValueError(f"{record_type.title()} not found: {record_id}")

        current_status = entity.state

        if args.status:
            # Transition to new status
            if args.dry_run:
                # Validate without executing
                is_valid, msg = validate_transition(
                    record_type or "task",
                    current_status,
                    args.status,
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
                    "valid": is_valid,
                    "message": msg,
                }) if formatter.json_mode else formatter.text(dry_run_text)
                return 0 if is_valid else 1

            # Execute transition with guard enforcement
            old_state = entity.state
            
            # Build context for guards
            context = {
                "task": {
                    "id": entity.id,
                    "status": old_state,
                    "state": old_state,
                    "session_id": entity.session_id,
                },
                "task_id": entity.id,
                "entity_type": record_type or "task",
                "entity_id": entity.id,
            }
            
            # Execute the transition with guard validation and action execution
            if not args.force:
                try:
                    # transition_entity validates guards and executes actions
                    transition_result = transition_entity(
                        entity_type=record_type or "task",
                        entity_id=entity.id,
                        to_state=args.status,
                        current_state=old_state,
                        context=context,
                    )
                except EntityTransitionError as e:
                    formatter.error(f"Transition blocked: {e}", error_code="guard_failed")
                    return 1
            else:
                # Force mode: skip validation
                transition_result = {"state": args.status, "previous_state": old_state}
            
            # Update and persist the entity
            entity.state = args.status
            entity.record_transition(old_state, args.status, reason="cli-status-command")
            repo.save(entity)

            formatter.json_output({
                "status": "transitioned",
                "record_id": record_id,
                "from_status": current_status,
                "to_status": args.status,
            }) if formatter.json_mode else formatter.text(
                f"Transitioned {record_id}: {current_status} -> {args.status}"
            )

        else:
            # Show current status
            status_text = f"Task: {record_id}\n"
            status_text += f"Type: {record_type or 'task'}\n"
            status_text += f"Status: {entity.state}"
            if hasattr(entity, "title") and entity.title:
                status_text += f"\nTitle: {entity.title}"
            if entity.session_id:
                status_text += f"\nSession: {entity.session_id}"

            formatter.json_output({
                "record_id": record_id,
                "record_type": record_type,
                "status": entity.state,
                "title": getattr(entity, "title", ""),
                "session_id": entity.session_id,
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
