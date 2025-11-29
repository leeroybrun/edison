"""
Edison session me command.

SUMMARY: Show or update current session identity/context
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session import lifecycle as session_manager
from edison.core.session import validate_session_id

SUMMARY = "Show or update current session identity/context"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--set",
        dest="set_session",
        metavar="SESSION_ID",
        help="Set the current session context",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the current session context",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Show/update session identity - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        if args.clear:
            # Clear current session context
            session_manager.clear_current_session()
            if formatter.json_mode:
                formatter.json_output({"status": "cleared"})
            else:
                formatter.text("Current session context cleared.")
            return 0

        if args.set_session:
            # Set current session context
            session_id = validate_session_id(args.set_session)
            session_manager.set_current_session(session_id)
            if formatter.json_mode:
                formatter.json_output({"status": "set", "session_id": session_id})
            else:
                formatter.text(f"Current session set to: {session_id}")
            return 0

        # Show current session
        current = session_manager.get_current_session()
        if current:
            session = session_manager.get_session(current)
            if formatter.json_mode:
                formatter.json_output({
                    "current_session": current,
                    "session": session,
                })
            else:
                formatter.text(f"Current session: {current}")
                formatter.text(f"Status: {session.get('status', 'unknown')}")
                if session.get("task"):
                    formatter.text(f"Task: {session.get('task')}")
                if session.get("owner"):
                    formatter.text(f"Owner: {session.get('owner')}")
                tasks = session.get("tasks", {})
                if tasks:
                    formatter.text(f"Tasks: {len(tasks)}")
        else:
            if formatter.json_mode:
                formatter.json_output({"current_session": None})
            else:
                formatter.text("No current session set.")
                formatter.text("\nUse 'edison session me --set <session_id>' to set one.")

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
