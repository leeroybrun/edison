"""
Edison session db create command.

SUMMARY: Create session database
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter

SUMMARY = "Create session database"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create session database - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session.persistence.database import create_session_database
    from edison.core.session.core.id import validate_session_id

    try:
        session_id = validate_session_id(args.session_id)
        db_url = create_session_database(session_id)

        if db_url:
            result = {
                "session_id": session_id,
                "database_url": db_url,
                "status": "created"
            }

            if formatter.json_mode:
                formatter.json_output(result)
            else:
                formatter.text(f"✓ Created database for session {session_id}")
                formatter.text(f"  Database URL: {db_url}")
        else:
            result = {
                "session_id": session_id,
                "status": "disabled",
                "message": "Database isolation not enabled"
            }

            if formatter.json_mode:
                formatter.json_output(result)
            else:
                formatter.text(f"Database isolation not enabled for session {session_id}")

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
