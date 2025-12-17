"""
Edison task similar command.

SUMMARY: Find similar/duplicate tasks across the entire project (global + sessions)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Find similar/duplicate tasks across the entire project"


def register_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--task",
        dest="task_id",
        help="Find similar tasks to an existing task id",
    )
    group.add_argument(
        "--query",
        dest="query",
        help="Free-text query (usually a task title) to match against existing tasks",
    )

    parser.add_argument(
        "--top",
        type=int,
        help="Maximum number of matches to return (default: from config)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Minimum similarity score (default: from config)",
    )
    parser.add_argument(
        "--only-todo",
        action="store_true",
        help="Only consider tasks in todo state",
    )
    parser.add_argument(
        "--states",
        type=str,
        help="Comma-separated list of task states to search (overrides --only-todo)",
    )

    add_json_flag(parser)
    add_repo_root_flag(parser)


def _parse_states(args: argparse.Namespace) -> list[str] | None:
    raw = (getattr(args, "states", None) or "").strip()
    if raw:
        return [s.strip() for s in raw.split(",") if s.strip()]
    if getattr(args, "only_todo", False):
        return ["todo"]
    return None


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        states = _parse_states(args)

        from edison.core.task.similarity import (
            find_similar_tasks_for_query,
            find_similar_tasks_for_task,
        )

        if getattr(args, "task_id", None):
            matches = find_similar_tasks_for_task(
                str(args.task_id),
                project_root=repo_root,
                threshold=getattr(args, "threshold", None),
                top_k=getattr(args, "top", None),
                states=states,
            )
            query_repr = {"taskId": str(args.task_id)}
        else:
            matches = find_similar_tasks_for_query(
                str(args.query),
                project_root=repo_root,
                threshold=getattr(args, "threshold", None),
                top_k=getattr(args, "top", None),
                states=states,
            )
            query_repr = {"query": str(args.query)}

        payload = {
            **query_repr,
            "count": len(matches),
            "matches": [
                {
                    "taskId": m.task_id,
                    "score": round(m.score, 2),
                    "title": m.title,
                    "state": m.state,
                    "sessionId": m.session_id,
                    "path": str(m.path.relative_to(repo_root)) if m.path.is_relative_to(repo_root) else str(m.path),
                    "scores": {"title": round(m.title_score, 2), "body": round(m.body_score, 2)},
                }
                for m in matches
            ],
        }

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(f"Matches: {payload['count']}")
            for m in payload["matches"]:
                sid = f" (session {m['sessionId']})" if m.get("sessionId") else ""
                formatter.text(f"- {m['taskId']}{sid}: {m['score']} — {m['title']}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="similar_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

