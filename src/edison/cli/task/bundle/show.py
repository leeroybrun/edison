"""
Edison task bundle show command.

SUMMARY: Show the resolved bundle root and members for a task
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Show the resolved bundle root and members for a task"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.task_id))

        from edison.core.qa.bundler.cluster import select_cluster

        selection = select_cluster(task_id, scope="bundle", project_root=project_root)
        cluster_ids = list(selection.task_ids)
        members = [t for t in cluster_ids if t != selection.root_task_id]

        payload = {
            "taskId": task_id,
            "rootTask": str(selection.root_task_id),
            "scope": "bundle",
            "members": members,
            "count": len(members),
        }
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(
                f"Bundle root: {selection.root_task_id}\n"
                f"Members ({len(members)}): " + (", ".join(members) if members else "(none)")
            )
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="task_bundle_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
