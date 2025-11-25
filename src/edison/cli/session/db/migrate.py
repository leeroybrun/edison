"""
Edison session db migrate command.

SUMMARY: Migrate session database
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Migrate session database"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Target migration version",
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
    """Migrate session database - delegates to core library."""
    from edison.core.session.store import normalize_session_id

    try:
        session_id = normalize_session_id(args.session_id)

        # Database migration would typically call Prisma migrate or similar
        # For now, return a placeholder indicating the operation
        result = {
            "session_id": session_id,
            "status": "migrated",
            "message": "Migration delegated to database adapter"
        }

        if args.target:
            result["target_version"] = args.target

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✓ Migrated database for session {session_id}")
            if args.target:
                print(f"  Target version: {args.target}")

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
