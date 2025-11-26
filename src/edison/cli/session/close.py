"""
Edison session close command.

SUMMARY: Validate and transition a session into closing/archival
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Validate and transition a session into closing/archival"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force the closing transition even when verification fails",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip guard checks and move directly to closing (not recommended)",
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
    """Close session - delegates to core library."""
    from edison.core.session import manager as session_manager
    from edison.core.session import store as session_store
    from edison.core.session.verify import verify_session_health

    try:
        session_id = session_store.validate_session_id(args.session_id)

        # Run verification unless explicitly skipped
        if not args.skip_validation:
            health = verify_session_health(session_id)

            if not health.get("ok") and not args.force:
                if args.json:
                    print(json.dumps({"error": "verification_failed", "health": health}, indent=2))
                else:
                    print(f"Session {session_id} failed verification:")
                    for detail in health.get("details", []):
                        print(f"  - {detail}")
                    print("\nUse --force to close anyway or fix the issues first.")
                return 1

        # Transition to closing
        session_manager.transition_session(session_id, "closing")

        if args.json:
            session = session_manager.get_session(session_id)
            print(json.dumps({"sessionId": session_id, "status": "closing", "session": session}, indent=2, default=str))
        else:
            print(f"Session {session_id} transitioned to closing.")

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
