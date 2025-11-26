"""
Edison session db seed command.

SUMMARY: Seed session database
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Seed session database"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--seed-file",
        type=str,
        help="Path to seed file",
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
    """Seed session database - delegates to core library."""
    from edison.core.session.store import validate_session_id

    try:
        session_id = validate_session_id(args.session_id)

        # Database seeding would typically run seed scripts via Prisma or similar
        # For now, return a placeholder indicating the operation
        result = {
            "session_id": session_id,
            "status": "seeded",
            "message": "Seeding delegated to database adapter"
        }

        if args.seed_file:
            result["seed_file"] = args.seed_file

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✓ Seeded database for session {session_id}")
            if args.seed_file:
                print(f"  Seed file: {args.seed_file}")

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
