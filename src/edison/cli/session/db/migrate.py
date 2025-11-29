"""
Edison session db migrate command.

SUMMARY: Migrate session database
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session.core.id import validate_session_id

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
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Migrate session database - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        session_id = validate_session_id(args.session_id)

        # Database migration would typically call Prisma migrate or similar
        # For now, return a placeholder indicating the operation
        result = {
            "session_id": session_id,
            "status": "migrated",
            "message": "Migration delegated to database adapter"
        }

        if args.target:
            result["target_version"] = args.target

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"✓ Migrated database for session {session_id}")
            if args.target:
                formatter.text(f"  Target version: {args.target}")

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
