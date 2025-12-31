"""
Edison task audit command.

SUMMARY: Audit `.project/tasks` for overlap, missing links, and duplicates
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.task.audit import audit_tasks

SUMMARY = "Audit `.project/tasks` for overlap, missing links, and duplicates"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tasks-root",
        type=str,
        help="Override tasks root (default: config-driven `.project/tasks`).",
    )
    parser.add_argument(
        "--include-session-tasks",
        action="store_true",
        help="Include session-scoped tasks in the audit (reserved for future use).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Duplicate/similarity threshold override (default: tasks config threshold).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Max duplicates per task (default: tasks config topK).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        tasks_root = Path(args.tasks_root).resolve() if getattr(args, "tasks_root", None) else None

        report = audit_tasks(
            project_root=project_root,
            tasks_root=tasks_root,
            include_session_tasks=bool(getattr(args, "include_session_tasks", False)),
            threshold=getattr(args, "threshold", None),
            top_k=getattr(args, "top_k", None),
        )

        payload = report.to_dict()
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text("Task Audit")
            formatter.text(f"Tasks: {payload['taskCount']}")
            formatter.text("")
            if payload.get("issues"):
                formatter.text(f"Issues: {len(payload['issues'])}")
                for issue in payload["issues"]:
                    formatter.text(f"- [{issue.get('severity','info')}] {issue.get('code')}: {issue.get('message')}")
            else:
                formatter.text("Issues: none")
            if payload.get("duplicates"):
                formatter.text("")
                formatter.text("Duplicates:")
                for d in payload["duplicates"]:
                    formatter.text(f"- {d['a']} <-> {d['b']} (score={d['score']})")

        return 0
    except Exception as exc:
        formatter.error(exc, error_code="audit_error")
        return 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    register_args(p)
    parsed = p.parse_args()
    sys.exit(main(parsed))

