"""
Edison session recovery recover command.

SUMMARY: Recover damaged session
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session.core.id import validate_session_id

SUMMARY = "Recover damaged session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session",
        dest="session_id",
        required=True,
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--restore-records",
        action="store_true",
        help="Restore records to global queues",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Recover damaged session - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        session_id = validate_session_id(args.session_id)
        from edison.core.session.lifecycle.recovery import recover_session
        from edison.core.utils.io import read_json

        recovery_path = recover_session(
            session_id,
            restore_records=bool(args.restore_records),
            reason="manual_recovery",
        )
        recovered_records = 0
        try:
            payload = read_json(recovery_path / "session.json")
            recovered_records = int((payload.get("meta") or {}).get("restoredRecords") or 0)
        except Exception:
            recovered_records = 0

        result = {
            "sessionId": session_id,
            "restoredRecords": recovered_records,
            "status": "recovered",
            "recoveryPath": str(recovery_path)
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            formatter.text(f"✓ Recovered session {session_id}")
            if recovered_records > 0:
                formatter.text(f"  Restored {recovered_records} record(s) to global queues")
            formatter.text(f"  Recovery path: {recovery_path}")

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
