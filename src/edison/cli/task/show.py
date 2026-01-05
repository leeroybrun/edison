"""
Edison task show command.

SUMMARY: Show raw task Markdown
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    format_display_path,
    get_repo_root,
    resolve_existing_task_id,
    resolve_session_id,
)

SUMMARY = "Show raw task Markdown"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "task_id",
        help="Task identifier (e.g., 150-wave1-auth-gate)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)

        from edison.core.task.repository import TaskRepository

        task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.task_id))
        repo = TaskRepository(project_root=project_root)
        path = repo.get_path(task_id)
        content = path.read_text(encoding="utf-8", errors="strict")

        task = repo.get(task_id)
        display_path = format_display_path(project_root=project_root, path=path)
        active_session_id = resolve_session_id(project_root=project_root, required=False)
        if (
            not formatter.json_mode
            and task
            and task.session_id
            and str(task.session_id) != str(active_session_id or "")
        ):
            print(
                f"Note: task is session-scoped (session={task.session_id}) at {display_path}",
                file=sys.stderr,
            )

        if formatter.json_mode:
            formatter.json_output(
                {
                    "recordType": "task",
                    "id": task_id,
                    "path": str(path),
                    "pathDisplay": display_path,
                    "task": task.to_dict() if task else None,
                    "content": content,
                }
            )
        else:
            formatter.text(content)
        return 0
    except Exception as e:
        formatter.error(e, error_code="task_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
