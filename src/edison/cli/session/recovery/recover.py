"""
Edison session recovery recover command.

SUMMARY: Recover damaged session
"""
from __future__ import annotations

import argparse
import json
import sys

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
    """Recover damaged session - delegates to core library."""
    from edison.core.session.recovery import restore_records_to_global_transactional
    from edison.core.session.store import (
        normalize_session_id,
        load_session,
        save_session,
        _move_session_json_to,
        _session_dir
    )
    from edison.core.utils.time import utc_timestamp

    try:
        session_id = normalize_session_id(args.session_id)

        recovered_records = 0
        if args.restore_records:
            recovered_records = restore_records_to_global_transactional(session_id)

        # Load and update session state
        session = load_session(session_id)
        session.setdefault("meta", {})["recoveredAt"] = utc_timestamp()
        session.setdefault("activityLog", []).insert(0, {
            "timestamp": utc_timestamp(),
            "message": f"Session recovered, restored {recovered_records} records"
        })
        save_session(session_id, session)

        # Move session to recovery directory
        _move_session_json_to("recovery", session_id)
        recovery_path = _session_dir("recovery", session_id)

        result = {
            "sessionId": session_id,
            "restoredRecords": recovered_records,
            "status": "recovered",
            "recoveryPath": str(recovery_path)
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"✓ Recovered session {session_id}")
            if recovered_records > 0:
                print(f"  Restored {recovered_records} record(s) to global queues")
            print(f"  Recovery path: {recovery_path}")

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
