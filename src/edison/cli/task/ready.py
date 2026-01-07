"""
Edison task ready command.

SUMMARY: List tasks ready to be claimed (completion moved to `task done`)
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
from edison.core.task import TaskQAWorkflow

SUMMARY = "List tasks ready to be claimed (completion moved to `task done`)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        nargs="?",
        help="(Deprecated) Task ID to complete (use `edison task done <task>`). If omitted, lists ready tasks.",
    )
    parser.add_argument(
        "--session",
        help="Filter by session",
    )
    parser.add_argument(
        "--skip-context7",
        action="store_true",
        help="DEPRECATED path: bypass Context7 checks (requires --skip-context7-reason). Prefer `edison task done`.",
    )
    parser.add_argument(
        "--skip-context7-reason",
        help="DEPRECATED path: justification for Context7 bypass.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="DEPRECATED: Use `edison evidence capture <task>` instead (this flag no longer runs automation).",
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
            session_id = resolve_session_id(
                project_root=project_root,
                explicit=args.session,
                required=True,
            )

            print(
                "DEPRECATED: `edison task ready <task>` completes tasks. "
                "Use `edison task done <task>` instead.",
                file=sys.stderr,
            )

            if bool(getattr(args, "run", False)):
                raise ValueError(
                    "`edison task ready --run` is no longer supported.\n"
                    "Use:\n"
                    "  - `edison qa round prepare <task>`\n"
                    "  - `edison evidence capture <task>`\n"
                    "  - `edison evidence status <task>`\n"
                    "Then review the evidence output and run `edison task done <task>`."
                )

            # Back-compat alias: delegate to task done, but keep legacy output shape.
            from edison.cli._utils import resolve_existing_task_id

            record_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.record_id))
            skip_context7 = bool(getattr(args, "skip_context7", False))
            skip_context7_reason = str(getattr(args, "skip_context7_reason", "") or "").strip()
            if skip_context7 and not skip_context7_reason:
                raise ValueError("--skip-context7 requires --skip-context7-reason")
            if (not skip_context7) and skip_context7_reason:
                raise ValueError("--skip-context7-reason requires --skip-context7")
            if skip_context7:
                print(
                    f"WARNING: bypassing Context7 checks for task {record_id} ({skip_context7_reason})",
                    file=sys.stderr,
                )
            workflow = TaskQAWorkflow(project_root=project_root)
            task_entity = workflow.complete_task(
                record_id,
                session_id,
                enforce_tdd=True,
                skip_context7=skip_context7,
                skip_context7_reason=skip_context7_reason,
            )

            payload = {
                "record_id": record_id,
                "ready": True,
                "state": task_entity.state,
                "session_id": session_id,
            }
            if skip_context7:
                payload["skip_context7"] = True
                payload["skip_context7_reason"] = skip_context7_reason

            formatter.json_output(payload) if formatter.json_mode else formatter.text(
                f"Task {record_id} marked as ready (moved to {task_entity.state})."
            )
            return 0

        else:
            # List all ready tasks (derived from dependency graph, not just todo state).
            from edison.core.task.readiness import TaskReadinessEvaluator

            # Listing is global by default. Only filter to a specific session when the user
            # explicitly requests it via --session.
            session_id = (
                resolve_session_id(project_root=project_root, explicit=args.session, required=False)
                if args.session
                else None
            )

            evaluator = TaskReadinessEvaluator(project_root=project_root)
            ready_tasks = [r.to_ready_list_dict() for r in evaluator.list_ready_tasks(session_id=session_id)]

            if ready_tasks:
                limit = 25
                shown = ready_tasks[:limit]
                list_text = f"Ready tasks ({len(ready_tasks)}):\n" + "\n".join(
                    f"  - {t['id']}: {t['title']}" for t in shown
                )
                if len(ready_tasks) > limit:
                    list_text += f"\n  ... and {len(ready_tasks) - limit} more (use --json for full list)"
            else:
                list_text = "No tasks ready to claim."

            if formatter.json_mode:
                formatter.json_output({"tasks": ready_tasks, "count": len(ready_tasks), "session_id": session_id})
            else:
                formatter.text(list_text)

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
