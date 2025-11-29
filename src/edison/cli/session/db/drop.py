"""
Edison session db drop command.

SUMMARY: Drop session database
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session.persistence.database import drop_session_database
from edison.core.session.core.id import validate_session_id

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
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Drop session database - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        session_id = validate_session_id(args.session_id)

        if not args.force:
            response = input(f"Drop database for session {session_id}? (y/N): ")
            if response.lower() != 'y':
                if formatter.json_mode:
                    formatter.json_output({"status": "cancelled"})
                else:
                    formatter.text("Operation cancelled")
                return 0

        drop_session_database(session_id)

        result = {
            "session_id": session_id,
            "status": "dropped"
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"✓ Dropped database for session {session_id}")

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
