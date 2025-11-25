"""
Edison task mark_delegated command.

SUMMARY: Mark task as delegated
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Mark task as delegated"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task ID to mark as delegated",
    )
    parser.add_argument(
        "--delegated-to",
        default="unassigned",
        help="Agent or user to whom task is delegated (default: unassigned)",
    )
    parser.add_argument(
        "--session",
        help="Session ID for context",
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
    """Mark task as delegated - delegates to core library."""
    from edison.core import task
    from edison.core.session import store as session_store

    try:
        # Normalize the task ID
        task_id = task.normalize_record_id("task", args.task_id)

        # Normalize session ID if provided
        session_id = None
        if args.session:
            session_id = session_store.normalize_session_id(args.session)

        # Find the task
        task_path = task.find_record(task_id, "task")
        metadata = task.read_metadata(task_path, "task")

        # Update metadata to mark as delegated
        # This requires updating the task markdown frontmatter
        # For now, we'll use the update_line function to add delegation metadata
        from edison.core.task import update_line, OWNER_PREFIX_TASK

        # Add delegation metadata after owner line
        delegation_line = f"delegated_to: {args.delegated_to}"
        if session_id:
            delegation_line += f"\ndelegated_in_session: {session_id}"

        # Read current content
        with open(task_path, 'r') as f:
            content = f.read()

        # Check if already delegated
        if "delegated_to:" in content:
            if args.json:
                print(json.dumps({
                    "status": "already_delegated",
                    "task_id": task_id,
                    "message": "Task already marked as delegated",
                }, indent=2))
            else:
                print(f"Task {task_id} is already marked as delegated")
            return 1

        # Insert delegation metadata
        lines = content.split('\n')
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            # Insert after Primary Model line or at beginning
            if not inserted and ("**Primary Model:**" in line or line.startswith(OWNER_PREFIX_TASK)):
                new_lines.append(f"  - **Delegated To:** {args.delegated_to}")
                if session_id:
                    new_lines.append(f"  - **Delegated In Session:** {session_id}")
                inserted = True

        # Write back
        with open(task_path, 'w') as f:
            f.write('\n'.join(new_lines))

        if args.json:
            print(json.dumps({
                "delegated": True,
                "taskId": task_id,
                "delegatedTo": args.delegated_to,
                "sessionId": session_id,
            }, indent=2))
        else:
            print(f"Marked task {task_id} as delegated to {args.delegated_to}")
            if session_id:
                print(f"Session: {session_id}")

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
