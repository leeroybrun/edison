"""
Edison task bundle remove command.

SUMMARY: Remove tasks from a validation bundle (clear bundle_root)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Remove tasks from a validation bundle (clear bundle_root)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "members",
        nargs="+",
        help="Member task ids to remove from any bundle (clears bundle_root)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _bundle_root_from_task(task: object) -> str | None:
    try:
        rels = getattr(task, "relationships", None) or []
        for e in rels:
            if isinstance(e, dict) and e.get("type") == "bundle_root":
                target = str(e.get("target") or "").strip()
                return target or None
    except Exception:
        return None
    return None


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)

        from edison.core.task.relationships.service import TaskRelationshipService
        from edison.core.task.repository import TaskRepository

        repo = TaskRepository(project_root=project_root)
        svc = TaskRelationshipService(project_root=project_root)

        removed: list[dict[str, str]] = []
        skipped: list[str] = []

        for raw in list(getattr(args, "members", []) or []):
            task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(raw))
            task = repo.get(task_id)
            if task is None:
                raise ValueError(f"Task not found: {task_id}")

            root = _bundle_root_from_task(task)
            if not root:
                skipped.append(task_id)
                continue

            svc.remove(task_id=task_id, rel_type="bundle_root", target_id=root)
            removed.append({"taskId": task_id, "rootTask": root})

        payload = {
            "status": "updated",
            "removed": removed,
            "skipped": skipped,
        }
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            lines = []
            for r in removed:
                lines.append(f"Removed {r['taskId']} from bundle root {r['rootTask']}")
            for s in skipped:
                lines.append(f"No bundle_root set for {s} (skipped)")
            formatter.text("\n".join(lines) if lines else "No changes.")

        return 0
    except Exception as exc:
        formatter.error(exc, error_code="task_bundle_remove_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
