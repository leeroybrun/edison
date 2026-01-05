"""
Edison task relate command.

SUMMARY: Add/remove non-blocking related-task links (canonical `relationships`)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.task import normalize_record_id

SUMMARY = "Add/remove non-blocking related-task links (canonical `relationships`)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_a", help="Task ID (A)")
    parser.add_argument("task_b", help="Task ID (B)")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the relation instead of adding it",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        a_id = normalize_record_id("task", args.task_a)
        b_id = normalize_record_id("task", args.task_b)
        if a_id == b_id:
            raise ValueError("Cannot relate a task to itself")

        remove = bool(getattr(args, "remove", False))

        from edison.core.task.relationships.service import TaskRelationshipService
        from edison.core.task.repository import TaskRepository

        svc = TaskRelationshipService(project_root=project_root)
        if remove:
            svc.remove(task_id=a_id, rel_type="related", target_id=b_id)
        else:
            svc.add(task_id=a_id, rel_type="related", target_id=b_id)

        repo = TaskRepository(project_root=project_root)
        a = repo.get(a_id)
        b = repo.get(b_id)
        if not a or not b:
            raise ValueError("Failed to reload tasks after relationship update")

        payload = {
            "status": "updated",
            "task_a": a_id,
            "task_b": b_id,
            "removed": remove,
            "a_related": list(a.related),
            "b_related": list(b.related),
        }
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            action = "Removed" if remove else "Added"
            formatter.text(f"{action} relation: {a_id} ↔ {b_id}")
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="relate_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
