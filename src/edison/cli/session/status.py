"""
Edison session status command.

SUMMARY: Display current session status
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session import lifecycle as session_manager
from edison.core.session.core.id import validate_session_id
from edison.core.session.current import get_current_session

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

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        session_id = args.session_id
        if session_id:
            session_id = validate_session_id(session_id)
        else:
            # Get current/active session using the proper resolver
            session_id = get_current_session()
            if not session_id:
                formatter.error("No active session found.", error_code="no_session")
                return 1

        # Get full session data
        session = session_manager.get_session(session_id)

        if formatter.json_mode:
            formatter.json_output(session)
        else:
            formatter.text(f"Session: {session_id}")
            # Session data uses 'state' not 'status' based on lifecycle/manager.py
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
