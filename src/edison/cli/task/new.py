"""
Edison task new command.

SUMMARY: Create a new task file using the project template
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task.manager import TaskManager

SUMMARY = "Create a new task file using the project template"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--id",
        dest="task_id",
        required=True,
        help="Priority slot (e.g., 150)",
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Task slug (e.g., auth-gate)",
    )
    parser.add_argument(
        "--wave",
        help="Wave identifier (e.g., wave1)",
    )
    parser.add_argument(
        "--type",
        dest="task_type",
        help="Task type (e.g., feature, bug, chore)",
    )
    parser.add_argument(
        "--owner",
        help="Owner name",
    )
    parser.add_argument(
        "--session",
        help="Session to create task in (creates in session todo queue)",
    )
    parser.add_argument(
        "--parent",
        help="Parent task ID for follow-up linking",
    )
    parser.add_argument(
        "--continuation-id",
        help="Continuation ID for downstream tools",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create new task - delegates to TaskManager."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Build task ID from components
        parts = [args.task_id]
        if args.wave:
            parts.append(args.wave)
        parts.append(args.slug)
        task_id = "-".join(parts)

        # Build title from type and slug
        task_type = args.task_type or "feature"
        title = f"{task_type.capitalize()}: {args.slug.replace('-', ' ')}"

        # Build description
        description = ""
        if args.owner:
            description += f"Owner: {args.owner}\n"
        if args.parent:
            description += f"Parent: {args.parent}\n"
        if args.session:
            description += f"Session: {args.session}\n"
        if args.continuation_id:
            description += f"Continuation ID: {args.continuation_id}\n"

        # Create task using TaskManager (uses TaskRepository.create_task)
        repo_root = get_repo_root(args)
        manager = TaskManager(project_root=repo_root)
        task_entity = manager.create_task(
            task_id=task_id,
            title=title,
            description=description.strip(),
            session_id=args.session,
            owner=args.owner,
        )

        # Get task file path (relative to project root for portability)
        task_path = manager._repo.get_path(task_entity.id)
        rel_path = task_path.relative_to(repo_root) if task_path.is_relative_to(repo_root) else task_path

        formatter.json_output({
            "status": "created",
            "task_id": task_entity.id,
            "state": task_entity.state,
            "title": task_entity.title,
            "path": str(rel_path),
        }) if formatter.json_mode else formatter.text(
            f"Created task: {task_entity.id} ({task_entity.state})\n  @{rel_path}"
        )

        return 0

    except Exception as e:
        formatter.error(e, error_code="create_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
