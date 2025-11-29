"""
Edison session close command.

SUMMARY: Validate and transition a session into closing/archival
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter

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
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Close session - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session import lifecycle as session_manager
    from edison.core.session.core.id import validate_session_id
    from edison.core.session.lifecycle.verify import verify_session_health

    try:
        session_id = validate_session_id(args.session_id)

        # Run verification unless explicitly skipped
        if not args.skip_validation:
            health = verify_session_health(session_id)

            if not health.get("ok") and not args.force:
                if formatter.json_mode:
                    formatter.json_output({"error": "verification_failed", "health": health})
                else:
                    formatter.text(f"Session {session_id} failed verification:")
                    for detail in health.get("details", []):
                        formatter.text(f"  - {detail}")
                    formatter.text("\nUse --force to close anyway or fix the issues first.")
                return 1

        # Transition to closing
        session_manager.transition_session(session_id, "closing")

        if formatter.json_mode:
            session = session_manager.get_session(session_id)
            formatter.json_output({"sessionId": session_id, "status": "closing", "session": session})
        else:
            formatter.text(f"Session {session_id} transitioned to closing.")

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
