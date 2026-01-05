"""
Edison task blocked command.

SUMMARY: List todo tasks blocked by unmet dependencies (and explain why)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    resolve_existing_task_id,
    resolve_session_id,
)

SUMMARY = "List todo tasks blocked by unmet dependencies (and explain why)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "record_id",
        nargs="?",
        help="Optional task id to explain (if omitted, lists all blocked todo tasks)",
    )
    parser.add_argument(
        "--session",
        help="Filter by session",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        session_id = (
            resolve_session_id(project_root=project_root, explicit=args.session, required=False)
            if args.session
            else None
        )

        from edison.core.task.readiness import TaskReadinessEvaluator

        evaluator = TaskReadinessEvaluator(project_root=project_root)

        if getattr(args, "record_id", None):
            task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.record_id))
            r = evaluator.evaluate_task(task_id)
            blocked = [b.to_dict() for b in r.blocked_by]
            is_blocked = bool(blocked)
            unmet = [
                {
                    "id": b.get("dependencyId"),
                    "state": b.get("dependencyState"),
                    "requiredStates": b.get("requiredStates", []),
                    "reason": b.get("reason", ""),
                }
                for b in blocked
            ]
            payload = {
                "id": r.task.id,
                "title": r.task.title or "",
                "state": r.task.state,
                # `ready` means "ready to claim" (only meaningful for todo tasks).
                "ready": r.ready,
                # `blocked` is the dependency-blocked signal for this command.
                "blocked": is_blocked,
                "blockedBy": blocked,
                "unmetDependencies": unmet,
            }
            if formatter.json_mode:
                formatter.json_output(payload)
            else:
                readiness = "BLOCKED" if is_blocked else "NOT BLOCKED"
                if is_blocked:
                    reason = "unmet dependencies"
                else:
                    reason = "dependency blocking applies to todo tasks only" if r.task.state != evaluator.todo_state() else "dependencies satisfied"
                formatter.text(f"{task_id}: {readiness} ({reason}; state={r.task.state})")
            return 0

        blocked = evaluator.list_blocked_tasks(session_id=session_id)
        tasks = [r.to_blocked_list_dict() for r in blocked]

        if formatter.json_mode:
            formatter.json_output({"tasks": tasks, "count": len(tasks), "session_id": session_id})
        else:
            if tasks:
                limit = 25
                shown = tasks[:limit]
                list_text = f"Blocked tasks ({len(tasks)}):\n" + "\n".join(
                    f"  - {t['id']}: {t['title']}" for t in shown
                )
                if len(tasks) > limit:
                    list_text += f"\n  ... and {len(tasks) - limit} more (use --json for full list)"
            else:
                list_text = "No blocked todo tasks."
            formatter.text(list_text)

        return 0
    except Exception as exc:
        formatter.error(exc, error_code="blocked_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
