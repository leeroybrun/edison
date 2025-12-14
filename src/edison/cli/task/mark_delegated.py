"""
Edison task mark_delegated command.

SUMMARY: Mark task as delegated
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task import TaskRepository, normalize_record_id
from edison.core.session import validate_session_id

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
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Mark task as delegated - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Normalize the task ID
        task_id = normalize_record_id("task", args.task_id)

        # Normalize session ID if provided
        session_id = None
        if args.session:
            session_id = validate_session_id(args.session)

        # Get the task using repository
        task_repo = TaskRepository(project_root=project_root)
        task_entity = task_repo.get(task_id)
        if not task_entity:
            raise ValueError(f"Task not found: {task_id}")

        # Check if already delegated
        if getattr(task_entity, "delegated_to", None):
            formatter.json_output({
                "status": "already_delegated",
                "task_id": task_id,
                "message": "Task already marked as delegated",
            }) if formatter.json_mode else formatter.text(
                f"Task {task_id} is already marked as delegated"
            )
            return 1

        # Update task entity with delegation info (persisted in YAML frontmatter)
        task_entity.delegated_to = args.delegated_to
        task_entity.delegated_in_session = session_id

        # Save updated task
        task_repo.save(task_entity)

        result_text = f"Marked task {task_id} as delegated to {args.delegated_to}"
        if session_id:
            result_text += f"\nSession: {session_id}"

        formatter.json_output({
            "delegated": True,
            "taskId": task_id,
            "delegatedTo": args.delegated_to,
            "sessionId": session_id,
        }) if formatter.json_mode else formatter.text(result_text)

        return 0

    except Exception as e:
        formatter.error(e, error_code="delegation_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
