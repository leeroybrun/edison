"""
Edison evidence init command.

SUMMARY: Initialize evidence directories for a task
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Initialize evidence directories for a task"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        raw_task_id = str(getattr(args, "task_id"))
        task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=raw_task_id)
        msg = (
            "`edison evidence init` is deprecated. "
            "Rounds and round-scoped reports are created via `edison qa round prepare <task>`."
        )
        if formatter.json_mode:
            formatter.json_output({"deprecated": True, "taskId": task_id, "message": msg, "use": "edison qa round prepare <task>"})
        else:
            formatter.text(msg)
        return 1

    except Exception as e:
        formatter.error(e, error_code="evidence_init_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
