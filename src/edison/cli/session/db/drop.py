"""
Edison session db drop command.

SUMMARY: Drop session database
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Drop session database"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force drop without confirmation",
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
    """Drop session database - delegates to core library."""
    from edison.core.session.database import drop_session_database
    from edison.core.session.store import validate_session_id

    try:
        session_id = validate_session_id(args.session_id)

        if not args.force:
            response = input(f"Drop database for session {session_id}? (y/N): ")
            if response.lower() != 'y':
                if args.json:
                    print(json.dumps({"status": "cancelled"}, indent=2))
                else:
                    print("Operation cancelled")
                return 0

        drop_session_database(session_id)

        result = {
            "session_id": session_id,
            "status": "dropped"
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✓ Dropped database for session {session_id}")

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
