"""
Edison task status command.

SUMMARY: Inspect or transition task/QA status with state-machine guards
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Inspect or transition task/QA status with state-machine guards"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task or QA identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--status",
        choices=["todo", "wip", "done", "validated", "waiting"],
        help="Transition to this status (if omitted, shows current status)",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        help="Record type (auto-detects if not provided)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview transition without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force transition even when guards fail",
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
    """Task status - delegates to core library."""
    from edison.core import task
    from pathlib import Path

    try:
        # Determine record type first
        record_type = args.type
        if not record_type:
            # Try to detect from the record_id string pattern
            record_type = task.detect_record_type(None, None) if "-qa" in args.record_id or args.record_id.endswith(".qa") else "task"
            if "-qa" in args.record_id or args.record_id.endswith(".qa"):
                record_type = "qa"
            else:
                record_type = "task"

        # Normalize the record ID
        record_id = task.normalize_record_id(record_type, args.record_id)

        # Find the record
        record_path = task.find_record(record_id, record_type or "task")
        metadata = task.read_metadata(record_path, record_type or "task")
        current_status = task.infer_status_from_path(record_path, record_type or "task")

        if args.status:
            # Transition to new status
            if args.dry_run:
                # Validate without executing
                is_valid, msg = task.validate_state_transition(
                    record_type or "task",
                    current_status,
                    args.status,
                )
                if args.json:
                    print(json.dumps({
                        "dry_run": True,
                        "record_id": record_id,
                        "current_status": current_status,
                        "target_status": args.status,
                        "valid": is_valid,
                        "message": msg,
                    }, indent=2))
                else:
                    if is_valid:
                        print(f"Transition {current_status} -> {args.status}: ALLOWED")
                    else:
                        print(f"Transition {current_status} -> {args.status}: BLOCKED - {msg}")
                return 0 if is_valid else 1

            # Execute transition (transition_task signature: task_id, to_state, config)
            task.transition_task(
                task_id=record_id,
                to_state=args.status,
            )

            if args.json:
                print(json.dumps({
                    "status": "transitioned",
                    "record_id": record_id,
                    "from_status": current_status,
                    "to_status": args.status,
                }, indent=2))
            else:
                print(f"Transitioned {record_id}: {current_status} -> {args.status}")

        else:
            # Show current status
            if args.json:
                print(json.dumps({
                    "record_id": record_id,
                    "record_type": record_type,
                    "status": current_status,
                    "path": str(record_path),
                    "metadata": {
                        "owner": metadata.owner,
                        "status": metadata.status,
                        "claimed_at": metadata.claimed_at,
                        "last_active": metadata.last_active,
                    },
                }, indent=2, default=str))
            else:
                print(f"Task: {record_id}")
                print(f"Type: {record_type or 'task'}")
                print(f"Status: {current_status}")
                print(f"Path: {record_path}")
                if metadata.owner:
                    print(f"Owner: {metadata.owner}")

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
