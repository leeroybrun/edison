"""
Edison session recovery recover command.

SUMMARY: Recover damaged session
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session.lifecycle.recovery import restore_records_to_global_transactional
from edison.core.session.core.id import validate_session_id
from edison.core.session.core.models import Session
from edison.core.utils.time import utc_timestamp

SUMMARY = "Recover damaged session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session",
        dest="session_id",
        required=True,
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--restore-records",
        action="store_true",
        help="Restore records to global queues",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Recover damaged session - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session.persistence.repository import SessionRepository

    try:
        session_id = validate_session_id(args.session_id)
        repo = SessionRepository()

        recovered_records = 0
        if args.restore_records:
            recovered_records = restore_records_to_global_transactional(session_id)

        # Load and update session state
        session_entity = repo.get(session_id)
        if not session_entity:
            raise ValueError(f"Session {session_id} not found")

        session = session_entity.to_dict()
        session.setdefault("meta", {})["recoveredAt"] = utc_timestamp()
        session.setdefault("activityLog", []).insert(0, {
            "timestamp": utc_timestamp(),
            "message": f"Session recovered, restored {recovered_records} records"
        })

        # Use transition_entity for proper guard and action execution
        from edison.core.state.transitions import transition_entity, EntityTransitionError
        from edison.core.config.domains.workflow import WorkflowConfig
        
        current_state = session.get("state", "active")
        recovery_state = WorkflowConfig().get_semantic_state("session", "recovery")
        
        try:
            result = transition_entity(
                entity_type="session",
                entity_id=session_id,
                to_state=recovery_state,
                current_state=current_state,
                context={
                    "session": session,
                    "session_id": session_id,
                    "reason": "manual_recovery",
                },
            )
            session["state"] = result["state"]
            if "history_entry" in result:
                session.setdefault("stateHistory", []).append(result["history_entry"])
        except EntityTransitionError as e:
            # For recovery, allow fallback to direct assignment since recovery
            # is meant to fix broken states
            session["state"] = recovery_state
        
        updated_entity = Session.from_dict(session)
        repo.save(updated_entity)

        recovery_path = repo.get_session_json_path(session_id).parent

        result = {
            "sessionId": session_id,
            "restoredRecords": recovered_records,
            "status": "recovered",
            "recoveryPath": str(recovery_path)
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"✓ Recovered session {session_id}")
            if recovered_records > 0:
                formatter.text(f"  Restored {recovered_records} record(s) to global queues")
            formatter.text(f"  Recovery path: {recovery_path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
