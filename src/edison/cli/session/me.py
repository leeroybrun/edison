"""
Edison session me command.

SUMMARY: Show or update current session identity/context
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Show/update session identity - delegates to core library."""
    from edison.core.session import manager as session_manager
    from edison.core.session import store as session_store

    try:
        if args.clear:
            # Clear current session context
            session_manager.clear_current_session()
            if args.json:
                print(json.dumps({"status": "cleared"}))
            else:
                print("Current session context cleared.")
            return 0

        if args.set_session:
            # Set current session context
            session_id = session_store.normalize_session_id(args.set_session)
            session_manager.set_current_session(session_id)
            if args.json:
                print(json.dumps({"status": "set", "session_id": session_id}))
            else:
                print(f"Current session set to: {session_id}")
            return 0

        # Show current session
        current = session_manager.get_current_session()
        if current:
            session = session_manager.get_session(current)
            if args.json:
                print(json.dumps({
                    "current_session": current,
                    "session": session,
                }, indent=2, default=str))
            else:
                print(f"Current session: {current}")
                print(f"Status: {session.get('status', 'unknown')}")
                if session.get("task"):
                    print(f"Task: {session.get('task')}")
                if session.get("owner"):
                    print(f"Owner: {session.get('owner')}")
                tasks = session.get("tasks", {})
                if tasks:
                    print(f"Tasks: {len(tasks)}")
        else:
            if args.json:
                print(json.dumps({"current_session": None}))
            else:
                print("No current session set.")
                print("\nUse 'edison session me --set <session_id>' to set one.")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
