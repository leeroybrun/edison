"""
Edison session cleanup_expired command.

SUMMARY: Detect and clean up expired sessions (restores records to global queues)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag
from edison.core.session.lifecycle.recovery import cleanup_expired_sessions

SUMMARY = "Detect and clean up expired sessions"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which sessions would be cleaned (no changes)",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        if args.dry_run:
            # Dry-run: report expired sessions without mutating state.
            # Core has a single mutation entrypoint; for dry-run we just check is_session_expired().
            from edison.core.session.lifecycle.recovery import is_session_expired
            from edison.core.session.persistence.repository import SessionRepository

            repo = SessionRepository()
            active_sessions = [s.id for s in repo.list_by_state("active")]
            expired = [sid for sid in active_sessions if is_session_expired(sid)]
            payload = {"expired": expired, "count": len(expired), "dry_run": True}
            if formatter.json_mode:
                formatter.json_output(payload)
            else:
                if expired:
                    formatter.text("Expired sessions (dry-run):")
                    for sid in expired:
                        formatter.text(f"  - {sid}")
                else:
                    formatter.text("No expired sessions detected.")
            return 0

        cleaned = cleanup_expired_sessions()
        payload = {"cleaned": cleaned, "count": len(cleaned)}
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            if cleaned:
                formatter.text("Cleaned expired sessions:")
                for sid in cleaned:
                    formatter.text(f"  - {sid}")
            else:
                formatter.text("No expired sessions cleaned.")
        return 0

    except Exception as e:
        formatter.error(e, error_code="cleanup_expired_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))


