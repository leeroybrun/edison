"""
Edison task list command.

SUMMARY: List tasks across queues
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "List tasks across queues"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--status",
        choices=["todo", "wip", "done", "validated", "waiting"],
        help="Filter by status",
    )
    parser.add_argument(
        "--session",
        help="Filter by session ID",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        default="task",
        help="Record type (default: task)",
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
    """List tasks - delegates to core library."""
    from edison.core import task
    from edison.core.session import store as session_store

    try:
        # Normalize session ID if provided
        session_id = None
        if args.session:
            session_id = session_store.validate_session_id(args.session)

        # List records
        records = task.list_records(
            record_type=args.type,
            session_id=session_id,
        )

        # Filter by status if specified
        if args.status:
            filtered_records = []
            for record in records:
                if record.status == args.status:
                    filtered_records.append(record)
            records = filtered_records

        if args.json:
            print(json.dumps({
                "records": [
                    {
                        "record_id": r.record_id,
                        "status": r.status,
                        "path": str(r.path),
                    }
                    for r in records
                ],
                "count": len(records),
                "filters": {
                    "status": args.status,
                    "session": session_id,
                    "type": args.type,
                },
            }, indent=2))
        else:
            if not records:
                print(f"No {args.type}s found")
                if args.status:
                    print(f"  (status filter: {args.status})")
                if session_id:
                    print(f"  (session filter: {session_id})")
            else:
                print(f"Found {len(records)} {args.type}(s):")
                for record in records:
                    print(f"  {record.record_id} [{record.status}]")

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
