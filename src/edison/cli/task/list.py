"""
Edison task list command.

SUMMARY: List tasks across queues
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root, get_repository

SUMMARY = "List tasks across queues"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--status",
        choices=["todo", "wip", "done", "validated", "waiting"],
        help="Filter by status",
    )
    parser.add_argument(
        "--session",
        help="Filter by session ID",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        default="task",
        help="Record type (default: task)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List tasks - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session import validate_session_id

    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Normalize session ID if provided
        session_id = None
        if args.session:
            session_id = validate_session_id(args.session)

        # Get repository based on type
        repo = get_repository(args.type, project_root=project_root)

        # List entities
        if args.status:
            entities = repo.list_by_state(args.status)
        else:
            entities = repo.get_all()

        # Filter by session if specified
        if session_id:
            entities = [e for e in entities if e.session_id == session_id]

        if not entities:
            list_text = f"No {args.type}s found"
            if args.status:
                list_text += f"\n  (status filter: {args.status})"
            if session_id:
                list_text += f"\n  (session filter: {session_id})"
        else:
            list_text = f"Found {len(entities)} {args.type}(s):\n" + "\n".join(
                f"  {entity.id} [{entity.state}]" for entity in entities
            )

        formatter.json_output({
            "records": [
                {
                    "record_id": e.id,
                    "status": e.state,
                    "title": getattr(e, "title", ""),
                }
                for e in entities
            ],
            "count": len(entities),
            "filters": {
                "status": args.status,
                "session": session_id,
                "type": args.type,
            },
        }) if formatter.json_mode else formatter.text(list_text)

        return 0

    except Exception as e:
        formatter.error(e, error_code="list_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
