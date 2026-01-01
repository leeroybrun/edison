"""
Edison session recovery recover_validation_tx command.

SUMMARY: Recover stuck validation transactions
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session.lifecycle.recovery import recover_incomplete_validation_transactions
from edison.core.session.core.id import validate_session_id

SUMMARY = "Recover stuck validation transactions"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--session",
        dest="session_id_flag",
        help="Session identifier (legacy flag alias for positional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List incomplete transactions without modifying anything (default when --force not set)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Abort and clean incomplete transactions",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Recover stuck validation transactions - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        raw = str(getattr(args, "session_id_flag", "") or getattr(args, "session_id", "") or "").strip()
        if not raw:
            raise ValueError("session_id is required (positional or --session)")
        session_id = validate_session_id(raw)

        dry_run = bool(args.dry_run) or not bool(args.force)
        recovered_count = recover_incomplete_validation_transactions(session_id, dry_run=dry_run)

        result = {
            "session_id": session_id,
            "recovered_transactions": recovered_count,
            "dry_run": dry_run,
            "status": "completed",
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if dry_run:
                formatter.text(
                    f"Incomplete validation transactions for session {session_id}: {recovered_count}"
                )
            else:
                if recovered_count > 0:
                    formatter.text(
                        f"✓ Recovered {recovered_count} validation transaction(s) for session {session_id}"
                    )
                else:
                    formatter.text(
                        f"No stuck validation transactions found for session {session_id}"
                    )

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
