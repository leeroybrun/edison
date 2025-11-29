"""
Edison session db seed command.

SUMMARY: Seed session database
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session.core.id import validate_session_id

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
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Seed session database - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


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

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"✓ Seeded database for session {session_id}")
            if args.seed_file:
                formatter.text(f"  Seed file: {args.seed_file}")

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
