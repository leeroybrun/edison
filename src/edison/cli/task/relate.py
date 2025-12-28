"""
Edison task relate command.

SUMMARY: Add/remove non-blocking related-task links (frontmatter `related`)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.task import normalize_record_id

SUMMARY = "Add/remove non-blocking related-task links (frontmatter `related`)"


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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        s = str(item).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        from edison.core.task.repository import TaskRepository

        repo = TaskRepository(project_root=project_root)
        a_id = normalize_record_id("task", args.task_a)
        b_id = normalize_record_id("task", args.task_b)
        if a_id == b_id:
            raise ValueError("Cannot relate a task to itself")

        a = repo.get(a_id)
        b = repo.get(b_id)
        if not a:
            raise ValueError(f"Task not found: {a_id}")
        if not b:
            raise ValueError(f"Task not found: {b_id}")

        remove = bool(getattr(args, "remove", False))

        a_related = list(getattr(a, "related", None) or [])
        b_related = list(getattr(b, "related", None) or [])

        if remove:
            a_related = [x for x in a_related if str(x).strip() != b_id]
            b_related = [x for x in b_related if str(x).strip() != a_id]
        else:
            a_related.append(b_id)
            b_related.append(a_id)

        a.related = _dedupe(a_related)
        b.related = _dedupe(b_related)

        repo.save(a)
        repo.save(b)

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

