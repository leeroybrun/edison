"""
Edison task ready command.

SUMMARY: List tasks ready to be claimed or check task readiness
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "List tasks ready to be claimed or check task readiness"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        nargs="?",
        help="Task ID to check readiness (if omitted, lists all ready tasks)",
    )
    parser.add_argument(
        "--session",
        dest="session_id",
        help="Filter by session",
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
    """List ready tasks or check readiness - delegates to core library."""
    from edison.core import task
    from edison.core.session import manager as session_manager

    try:
        if args.record_id:
            # Ready a specific task (move from wip -> done)
            # Normalize the record ID
            record_id = task.normalize_record_id("task", args.record_id)

            # Get session ID
            session_id = args.session_id
            if not session_id:
                session_id = session_manager.get_current_session()

            if not session_id:
                raise ValueError("No session specified and no current session found. Use --session to specify one.")

            # Ready the task (core function signature: task_id, session_id)
            src_path, dst_path = task.ready_task(record_id, session_id)

            if args.json:
                print(json.dumps({
                    "record_id": record_id,
                    "ready": True,
                    "source_path": str(src_path),
                    "destination_path": str(dst_path),
                }, indent=2, default=str))
            else:
                print(f"Task {record_id} marked as ready (moved to done).")
                print(f"Moved: {src_path} -> {dst_path}")
            return 0

        else:
            # List all ready tasks (tasks in todo status)
            records = task.list_records("task")
            ready_tasks = []

            for record in records:
                # Filter for todo status
                if record.status == "todo":
                    ready_tasks.append({
                        "id": record.record_id,
                        "path": str(record.path),
                        "status": record.status,
                    })

            if args.json:
                print(json.dumps({"tasks": ready_tasks}, indent=2))
            else:
                if ready_tasks:
                    print(f"Ready tasks ({len(ready_tasks)}):")
                    for t in ready_tasks:
                        print(f"  - {t['id']}")
                else:
                    print("No tasks ready to claim.")

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
