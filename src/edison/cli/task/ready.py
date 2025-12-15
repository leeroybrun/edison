"""
Edison task ready command.

SUMMARY: List tasks ready to be claimed or mark task as ready (complete)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    resolve_session_id,
)
from edison.core.task import TaskQAWorkflow, TaskRepository, normalize_record_id
from edison.core.config.domains.workflow import WorkflowConfig

SUMMARY = "List tasks ready to be claimed or mark task as ready (complete)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        nargs="?",
        help="Task ID to mark as ready/complete (if omitted, lists all ready tasks)",
    )
    parser.add_argument(
        "--session",
        help="Filter by session",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List ready tasks or mark task as ready - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        if args.record_id:
            # Ready/complete a specific task (move from wip -> done)
            record_id = normalize_record_id("task", args.record_id)

            session_id = resolve_session_id(
                project_root=project_root,
                explicit=args.session,
                required=True,
            )

            # Use TaskQAWorkflow.complete_task() to move from wip -> done
            workflow = TaskQAWorkflow(project_root=project_root)
            task_entity = workflow.complete_task(record_id, session_id)

            formatter.json_output({
                "record_id": record_id,
                "ready": True,
                "state": task_entity.state,
                "session_id": session_id,
            }) if formatter.json_mode else formatter.text(
                f"Task {record_id} marked as ready (moved to {task_entity.state})."
            )
            return 0

        else:
            # List all ready tasks (tasks in todo status)
            repo = TaskRepository(project_root=project_root)
            todo_state = WorkflowConfig().get_semantic_state("task", "todo")
            tasks = repo.list_by_state(todo_state)

            ready_tasks = [
                {
                    "id": t.id,
                    "title": t.title,
                    "state": t.state,
                }
                for t in tasks
            ]

            if ready_tasks:
                list_text = f"Ready tasks ({len(ready_tasks)}):\n" + "\n".join(
                    f"  - {t['id']}: {t['title']}" for t in ready_tasks
                )
            else:
                list_text = "No tasks ready to claim."

            formatter.json_output({"tasks": ready_tasks}) if formatter.json_mode else formatter.text(list_text)

            return 0

    except Exception as e:
        formatter.error(e, error_code="ready_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
