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
        help="Session identifier (e.g., sess-001)",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Recover stuck validation transactions - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        session_id = validate_session_id(args.session_id)
        recovered_count = recover_incomplete_validation_transactions(session_id)

        result = {
            "session_id": session_id,
            "recovered_transactions": recovered_count,
            "status": "completed"
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if recovered_count > 0:
                formatter.text(f"✓ Recovered {recovered_count} validation transaction(s) for session {session_id}")
            else:
                formatter.text(f"No stuck validation transactions found for session {session_id}")

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
