"""
Edison session status command.

SUMMARY: Display current session status
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter

SUMMARY = "Display current session status"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID (optional, uses current session if not specified)",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Display session status - delegates to core library."""
    from edison.core.session import manager as session_manager
    from edison.core.session.id import validate_session_id

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        session_id = args.session_id
        if session_id:
            session_id = validate_session_id(session_id)
            session = session_manager.get_session(session_id)
        else:
            # Get current/active session
            sessions = session_manager.list_sessions()
            active = [s for s in sessions if s.get("status") == "active"]
            if active:
                session = active[0]
                session_id = session.get("id", "unknown")
            else:
                formatter.error("No active session found.", error_code="no_session")
                return 1

        if formatter.json_mode:
            formatter.json_output(session)
        else:
            formatter.text(f"Session: {session_id}")
            formatter.text(f"Status: {session.get('status', 'unknown')}")
            if session.get("task"):
                formatter.text(f"Task: {session.get('task')}")
            if session.get("owner"):
                formatter.text(f"Owner: {session.get('owner')}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
