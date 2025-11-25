"""
Edison task split command.

SUMMARY: Split task into subtasks
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Split task into subtasks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task ID to split",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=2,
        help="Number of subtasks to create (default: 2)",
    )
    parser.add_argument(
        "--prefix",
        help="Prefix for child task IDs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview split without creating tasks",
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
    """Split task - delegates to core library."""
    from edison.core import task

    try:
        # Normalize the task ID
        task_id = task.normalize_record_id("task", args.task_id)

        # Find the task
        task_path = task.find_record(task_id, "task")
        metadata = task.read_metadata(task_path, "task")

        # Generate child IDs
        child_ids = []
        for i in range(args.count):
            child_id = task.next_child_id(task_id, prefix=args.prefix)
            child_ids.append(child_id)

        if args.dry_run:
            if args.json:
                print(json.dumps({
                    "dry_run": True,
                    "parent_id": task_id,
                    "child_ids": child_ids,
                    "count": args.count,
                }, indent=2))
            else:
                print(f"Would split {task_id} into {args.count} subtasks:")
                for child_id in child_ids:
                    print(f"  - {child_id}")
            return 0

        # Create child tasks
        created = []
        for i, child_id in enumerate(child_ids):
            # Create task with parent reference
            # create_task signature: task_id, title, description
            description = f"Subtask {i+1} of {args.count}\nParent: {task_id}"
            child_path = task.create_task(
                task_id=child_id,
                title=f"Part {i+1}",
                description=description,
            )
            created.append(child_id)

        if args.json:
            print(json.dumps({
                "status": "split",
                "parent_id": task_id,
                "child_ids": created,
                "count": len(created),
            }, indent=2))
        else:
            print(f"Split {task_id} into {len(created)} subtasks:")
            for child_id in created:
                print(f"  - {child_id}")

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
