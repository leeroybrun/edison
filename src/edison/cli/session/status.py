"""
Edison session status command.

SUMMARY: Display current session status
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Display current session status"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID (optional, uses current session if not specified)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )


def main(args: argparse.Namespace) -> int:
    """Display session status - delegates to core library."""
    from edison.core.session import manager as session_manager
    from edison.core.session import store as session_store

    try:
        session_id = args.session_id
        if session_id:
            session_id = session_store.normalize_session_id(session_id)
            session = session_manager.get_session(session_id)
        else:
            # Get current/active session
            sessions = session_manager.list_sessions()
            active = [s for s in sessions if s.get("status") == "active"]
            if active:
                session = active[0]
                session_id = session.get("id", "unknown")
            else:
                print("No active session found.")
                return 1

        if args.json:
            print(json.dumps(session, indent=2, default=str))
        else:
            print(f"Session: {session_id}")
            print(f"Status: {session.get('status', 'unknown')}")
            if session.get("task"):
                print(f"Task: {session.get('task')}")
            if session.get("owner"):
                print(f"Owner: {session.get('owner')}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
