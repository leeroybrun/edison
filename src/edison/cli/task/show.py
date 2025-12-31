"""
Edison task show command.

SUMMARY: Show raw task Markdown
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

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

        from edison.core.task import normalize_record_id
        from edison.core.task.repository import TaskRepository

        task_id = normalize_record_id("task", str(args.task_id))
        repo = TaskRepository(project_root=project_root)
        path = repo.get_path(task_id)
        content = path.read_text(encoding="utf-8", errors="strict")

        if formatter.json_mode:
            task = repo.get(task_id)
            formatter.json_output(
                {
                    "recordType": "task",
                    "id": task_id,
                    "path": str(path),
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

