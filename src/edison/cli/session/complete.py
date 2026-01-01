"""
Edison session complete command.

SUMMARY: Verify and promote a session to validated (finalize close-out)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag
from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.session import lifecycle as session_manager
from edison.core.session.core.id import validate_session_id
from edison.core.session.lifecycle.verify import verify_session_health

SUMMARY = "Verify and promote a session to validated"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force completion even when verification fails (not recommended)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip verification (not recommended)",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        session_id = validate_session_id(args.session_id)

        # Verify unless explicitly skipped
        if not args.skip_validation:
            health = verify_session_health(session_id)
            if not health.get("ok") and not args.force:
                if formatter.json_mode:
                    formatter.json_output({"error": "verification_failed", "health": health})
                else:
                    formatter.text(f"Session {session_id} failed verification:")
                    for detail in health.get("details", []):
                        formatter.text(f"  - {detail}")
                    formatter.text("\nUse --force to complete anyway or fix the issues first.")
                return 1

        # Restore session-scoped records back to global queues before completing.
        # This is part of the session lifecycle contract: the session tree provides
        # isolation while active, and on close-out we restore all session-owned
        # records to the global queues transactionally (FAIL-CLOSED by default).
        try:
            from edison.core.session.lifecycle.recovery import (
                restore_records_to_global_transactional,
            )

            restore_records_to_global_transactional(session_id)
        except Exception as e:
            if not args.force:
                formatter.error(e, error_code="restore_error")
                return 1

        sess = session_manager.get_session(session_id)
        current_state = str(sess.get("state") or "")

        workflow = WorkflowConfig()
        closing_state = workflow.get_semantic_state("session", "closing")
        validated_state = workflow.get_semantic_state("session", "validated")

        # When forced, bypass state-machine conditions/guards and directly persist
        # the validated state (still recording a transition for auditability).
        if args.force:
            from edison.core.session.persistence.repository import SessionRepository
            from edison.core.utils.paths import PathResolver

            repo = SessionRepository(project_root=PathResolver.resolve_project_root())
            entity = repo.get_or_raise(session_id)
            old = str(entity.state or "")
            if old != validated_state:
                try:
                    entity.record_transition(old, validated_state, reason="cli-force-complete")
                except Exception:
                    pass
                entity.state = validated_state
                repo.save(entity)
        else:
            # Ensure we're in closing before marking validated (follow state machine ordering).
            if current_state and current_state != closing_state and current_state != validated_state:
                session_manager.transition_session(session_id, closing_state)

            # Promote to validated (final close-out)
            if current_state != validated_state:
                session_manager.transition_session(session_id, validated_state)

        updated = session_manager.get_session(session_id)
        payload = {"sessionId": session_id, "status": validated_state, "session": updated}

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(f"Session {session_id} promoted to {validated_state}.")

        return 0

    except Exception as e:
        formatter.error(e, error_code="session_complete_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))






