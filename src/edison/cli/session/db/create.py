"""
Edison session db create command.

SUMMARY: Create session database
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Create session database"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
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
    """Create session database - delegates to core library."""
    from edison.core.session.database import create_session_database
    from edison.core.session.store import normalize_session_id

    try:
        session_id = normalize_session_id(args.session_id)
        db_url = create_session_database(session_id)

        if db_url:
            result = {
                "session_id": session_id,
                "database_url": db_url,
                "status": "created"
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"✓ Created database for session {session_id}")
                print(f"  Database URL: {db_url}")
        else:
            result = {
                "session_id": session_id,
                "status": "disabled",
                "message": "Database isolation not enabled"
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Database isolation not enabled for session {session_id}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
