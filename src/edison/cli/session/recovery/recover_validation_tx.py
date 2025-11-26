"""
Edison session recovery recover_validation_tx command.

SUMMARY: Recover stuck validation transactions
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Recover stuck validation transactions"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
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
    """Recover stuck validation transactions - delegates to core library."""
    from edison.core.session.recovery import recover_incomplete_validation_transactions
    from edison.core.session.store import validate_session_id

    try:
        session_id = validate_session_id(args.session_id)
        recovered_count = recover_incomplete_validation_transactions(session_id)

        result = {
            "session_id": session_id,
            "recovered_transactions": recovered_count,
            "status": "completed"
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if recovered_count > 0:
                print(f"✓ Recovered {recovered_count} validation transaction(s) for session {session_id}")
            else:
                print(f"No stuck validation transactions found for session {session_id}")

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
