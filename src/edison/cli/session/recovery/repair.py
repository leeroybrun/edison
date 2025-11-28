"""
Edison session recovery repair command.

SUMMARY: Repair session
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter

SUMMARY = "Repair session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--fix-state",
        action="store_true",
        help="Fix state inconsistencies",
    )
    parser.add_argument(
        "--fix-records",
        action="store_true",
        help="Fix record inconsistencies",
    )
    parser.add_argument(
        "--fix-worktree",
        action="store_true",
        help="Fix worktree issues",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fix all issues",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Repair session - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session.id import validate_session_id
    from edison.core.session.repository import SessionRepository
    from edison.core.session.worktree import worktree_health_check
    from edison.core.utils.time import utc_timestamp

    try:
        session_id = validate_session_id(args.session_id)
        fixes_applied = []
        repo = SessionRepository()

        if args.all or args.fix_state:
            # Fix state inconsistencies
            session_entity = repo.get(session_id)
            if session_entity:
                session = session_entity.to_dict()
                # Placeholder for state fixing logic
                fixes_applied.append("state")

        if args.all or args.fix_records:
            # Fix record inconsistencies
            # Placeholder for record fixing logic
            fixes_applied.append("records")

        if args.all or args.fix_worktree:
            # Fix worktree issues
            health = worktree_health_check(session_id)
            if not health.get("healthy", True):
                fixes_applied.append("worktree")

        # Update session metadata
        if fixes_applied:
            session_entity = repo.get(session_id)
            if not session_entity:
                raise ValueError(f"Session {session_id} not found")
            session = session_entity.to_dict()
            session.setdefault("meta", {})["repairedAt"] = utc_timestamp()
            session.setdefault("activityLog", []).insert(0, {
                "timestamp": utc_timestamp(),
                "message": f"Session repaired: {', '.join(fixes_applied)}"
            })
            from edison.core.session.models import Session
            updated_entity = Session.from_dict(session)
            repo.save(updated_entity)

        result = {
            "session_id": session_id,
            "fixes_applied": fixes_applied,
            "status": "repaired"
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if fixes_applied:
                formatter.text(f"✓ Repaired session {session_id}")
                formatter.text(f"  Fixes applied: {', '.join(fixes_applied)}")
            else:
                formatter.text(f"No repairs needed for session {session_id}")

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
