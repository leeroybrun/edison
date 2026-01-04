"""
Edison task list command.

SUMMARY: List tasks across queues
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    get_repository,
)

SUMMARY = "List tasks across queues"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--status",
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


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Validate status against config-driven states (do this at runtime to keep CLI startup fast)
        if args.status:
            from edison.core.config.domains.workflow import WorkflowConfig

            cfg = WorkflowConfig(repo_root=project_root)
            valid = sorted(set(cfg.get_states("task") + cfg.get_states("qa")))
            if args.status not in valid:
                raise ValueError(
                    f"Invalid status: {args.status}. Valid values: {', '.join(valid)}"
                )

        # Normalize session ID if provided
        session_id = None
        if args.session:
            # Import lazily to keep CLI startup fast for common invocations.
            from edison.core.session import validate_session_id

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
            lines = []
            any_session_scoped = False
            for entity in entities:
                sess = getattr(entity, "session_id", None)
                if sess:
                    any_session_scoped = True
                suffix = f" (session={sess})" if sess else ""
                lines.append(f"  {entity.id} [{entity.state}]{suffix}")

            list_text = f"Found {len(entities)} {args.type}(s):\n" + "\n".join(lines)
            if any_session_scoped:
                list_text += (
                    "\nNote: session-scoped records are stored under `.project/sessions/<state>/<session-id>/...`."
                )

        if formatter.json_mode:
            records = []
            for e in entities:
                try:
                    p = repo.get_path(e.id)
                    path_str = str(p.relative_to(project_root)) if p.is_relative_to(project_root) else str(p)
                except Exception:
                    path_str = ""

                owner = None
                try:
                    owner = e.metadata.created_by if getattr(e, "metadata", None) else None
                except Exception:
                    owner = None

                records.append(
                    {
                        "id": e.id,
                        "type": args.type,
                        "state": e.state,
                        "title": getattr(e, "title", ""),
                        "owner": owner,
                        "session_id": getattr(e, "session_id", None),
                        "path": path_str,
                    }
                )
            formatter.json_output(records)
        else:
            formatter.text(list_text)

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
