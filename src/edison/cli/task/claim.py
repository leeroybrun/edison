"""
Edison task claim command.

SUMMARY: Claim task or QA into a session with guarded status updates
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Claim task or QA into a session with guarded status updates"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task or QA identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--session",
        dest="session_id",
        help="Session to claim into (auto-detects if not provided)",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        help="Record type (auto-detects if not provided)",
    )
    parser.add_argument(
        "--owner",
        help="Owner name to stamp (defaults to git user or system user)",
    )
    parser.add_argument(
        "--status",
        default="wip",
        choices=["wip"],
        help="Target status after claim (default: wip)",
    )
    parser.add_argument(
        "--reclaim",
        action="store_true",
        help="Allow reclaiming from another active session",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force claim even with warnings",
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
    """Claim task - delegates to core library."""
    from edison.core import task
    from edison.core.session import manager as session_manager
    from edison.core.session import store as session_store

    try:
        # Determine record type first
        record_type = args.type
        if not record_type:
            # Try to detect from the record_id string pattern
            if "-qa" in args.record_id or args.record_id.endswith(".qa"):
                record_type = "qa"
            else:
                record_type = "task"

        # Normalize the record ID
        record_id = task.normalize_record_id(record_type, args.record_id)

        # Get or auto-detect session
        session_id = args.session_id
        if session_id:
            session_id = session_store.normalize_session_id(session_id)
        else:
            # Try to get current session
            session_id = session_manager.get_current_session()

        if not session_id:
            raise ValueError("No session specified and no current session found. Use --session to specify one.")

        # Get owner
        owner = args.owner or task.default_owner()

        # Claim the task (core function signature: task_id, session_id)
        # The core claim_task only moves files, doesn't handle metadata
        src_path, dst_path = task.claim_task(
            task_id=record_id,
            session_id=session_id,
        )

        # Update metadata with owner and timestamp
        metadata = task.read_metadata(dst_path, record_type or "task")

        # Ensure session block exists in the file and update owner
        lines = dst_path.read_text().splitlines(keepends=True)
        task.ensure_session_block(lines)

        # Update owner and timestamp fields using proper prefixes
        from datetime import datetime, timezone
        task.update_line(lines, task.OWNER_PREFIX_TASK, owner, skip_if_set=False)
        task.update_line(lines, task.CLAIMED_PREFIX, datetime.now(timezone.utc).isoformat(), skip_if_set=False)

        dst_path.write_text("".join(lines))

        if args.json:
            print(json.dumps({
                "status": "claimed",
                "record_id": record_id,
                "record_type": record_type,
                "session_id": session_id,
                "owner": owner,
                "source_path": str(src_path),
                "destination_path": str(dst_path),
            }, indent=2, default=str))
        else:
            print(f"Claimed {record_type or 'task'} {record_id}")
            if session_id:
                print(f"Session: {session_id}")
            print(f"Owner: {owner}")
            print(f"Status: {args.status}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, file=sys.stderr, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
