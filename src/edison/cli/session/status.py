"""
Edison session status command.

SUMMARY: Display current session status
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Display current session status"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID (optional, uses current session if not specified)",
    )
    parser.add_argument(
        "--status",
        help="Transition session to this state (if omitted, shows current status)",
    )
    parser.add_argument(
        "--reason",
        help="Reason for transition (recorded in session history)",
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
    """Display or transition session status."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        from edison.core.session.core.id import validate_session_id
        from edison.core.session.current import get_current_session
        from edison.core.session.persistence.repository import SessionRepository

        session_id = args.session_id
        if session_id:
            session_id = validate_session_id(session_id)
        else:
            # Get current/active session using the proper resolver
            session_id = get_current_session()
            if not session_id:
                formatter.error("No active session found.", error_code="no_session")
                return 1

        project_root = get_repo_root(args)
        repo = SessionRepository(project_root=project_root)
        entity = repo.get(session_id)
        if not entity:
            raise ValueError(f"Session not found: {session_id}")

        current_state = str(entity.state or "")

        if getattr(args, "status", None):
            # Validate status against config-driven states (runtime validation for fast CLI startup)
            from edison.core.config.domains.workflow import WorkflowConfig

            cfg = WorkflowConfig(repo_root=project_root)
            valid = cfg.get_states("session")
            if args.status not in valid:
                raise ValueError(
                    f"Invalid status for session: {args.status}. Valid values: {', '.join(valid)}"
                )

            if args.dry_run:
                from edison.core.state.transitions import validate_transition

                is_valid, msg = validate_transition("session", current_state, args.status)
                formatter.json_output({
                    "dry_run": True,
                    "session_id": session_id,
                    "current_status": current_state,
                    "target_status": args.status,
                    "valid": is_valid,
                    "message": msg,
                }) if formatter.json_mode else formatter.text(
                    f"Transition {current_state} -> {args.status}: "
                    + ("ALLOWED" if is_valid else f"BLOCKED - {msg}")
                )
                return 0 if is_valid else 1

            # Execute transition with guard enforcement (unless forced)
            if not args.force:
                from edison.core.state.transitions import transition_entity, EntityTransitionError

                context = {
                    "session_id": session_id,
                    "session": entity.to_dict(),
                    "entity_type": "session",
                    "entity_id": session_id,
                }
                if getattr(args, "reason", None):
                    context["reason"] = args.reason

                try:
                    transition_entity(
                        entity_type="session",
                        entity_id=session_id,
                        to_state=args.status,
                        current_state=current_state,
                        context=context,
                    )
                except EntityTransitionError as e:
                    formatter.error(f"Transition blocked: {e}", error_code="guard_failed")
                    return 1

            # Update and persist session
            entity.record_transition(
                current_state,
                args.status,
                reason=getattr(args, "reason", None) or "cli-session-status",
            )
            entity.state = args.status
            repo.save(entity)

            payload = {"status": "transitioned", "session_id": session_id, "from": current_state, "to": args.status}
            formatter.json_output(payload) if formatter.json_mode else formatter.text(
                f"Transitioned session {session_id}: {current_state} -> {args.status}"
            )
            return 0

        session = entity.to_dict()

        if formatter.json_mode:
            formatter.json_output(session)
        else:
            formatter.text(f"Session: {session_id}")
            state = session.get("state") or session.get("meta", {}).get("status", "unknown")
            formatter.text(f"Status: {state}")
            task = session.get("task") or session.get("meta", {}).get("task")
            if task:
                formatter.text(f"Task: {task}")
            owner = session.get("owner") or session.get("meta", {}).get("owner")
            if owner:
                formatter.text(f"Owner: {owner}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
