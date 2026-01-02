"""
Edison task new command.

SUMMARY: Create a new task file using the project template
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task.manager import TaskManager

SUMMARY = "Create a new task file using the project template"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--id",
        dest="task_id",
        required=True,
        help="Priority slot (e.g., 150)",
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Task slug (e.g., auth-gate)",
    )
    parser.add_argument(
        "--wave",
        help="Wave identifier (e.g., wave1)",
    )
    parser.add_argument(
        "--type",
        dest="task_type",
        help="Task type (e.g., feature, bug, chore)",
    )
    parser.add_argument(
        "--owner",
        help="Owner name",
    )
    parser.add_argument(
        "--session",
        help="Session to create task in (creates in session todo queue)",
    )
    parser.add_argument(
        "--parent",
        help="Parent task ID for follow-up linking",
    )
    parser.add_argument(
        "--continuation-id",
        help="Continuation ID for downstream tools",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip pre-create duplicate checks (if configured)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create new task - delegates to TaskManager."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Build task ID from components
        parts = [args.task_id]
        if args.wave:
            parts.append(args.wave)
        parts.append(args.slug)
        task_id = "-".join(parts)
        # Validate (reject whitespace/path separators, etc.)
        from edison.core.task import normalize_record_id
        task_id = normalize_record_id("task", task_id)

        # Build title from type and slug
        task_type = args.task_type or "feature"
        title = f"{task_type.capitalize()}: {args.slug.replace('-', ' ')}"

        # Build description
        description = ""
        if args.owner:
            description += f"Owner: {args.owner}\n"
        if args.session:
            description += f"Session: {args.session}\n"

        parent_id = None
        if args.parent:
            parent_id = normalize_record_id("task", args.parent)

        # Create task using TaskManager (uses TaskRepository.create_task)
        repo_root = get_repo_root(args)

        duplicates = []
        if not bool(getattr(args, "force", False)):
            try:
                from edison.core.task.duplication import DuplicateTaskError, check_duplicates_or_raise

                # Use the same title/description that would be created.
                duplicates = check_duplicates_or_raise(
                    title=title,
                    description=description.strip(),
                    project_root=repo_root,
                )
            except DuplicateTaskError as exc:
                if formatter.json_mode:
                    formatter.json_output(
                        {
                            "error": "duplicate_task",
                            "message": str(exc),
                            "duplicates": [
                                {
                                    "taskId": m.task_id,
                                    "score": round(m.score, 2),
                                    "title": m.title,
                                    "state": m.state,
                                }
                                for m in exc.matches
                            ],
                        }
                    )
                else:
                    formatter.error(exc, error_code="duplicate_task")
                return 1
            except Exception:
                # Fail-open: duplicate checks must not break task creation.
                duplicates = []

        manager = TaskManager(project_root=repo_root)
        task_entity = manager.create_task(
            task_id=task_id,
            title=title,
            description=description.strip(),
            session_id=args.session,
            owner=args.owner,
            parent_id=parent_id,
            continuation_id=args.continuation_id,
        )

        # Get task file path (relative to project root for portability)
        task_path = manager._repo.get_path(task_entity.id)
        rel_path = task_path.relative_to(repo_root) if task_path.is_relative_to(repo_root) else task_path

        result = {
            "status": "created",
            "task_id": task_entity.id,
            "state": task_entity.state,
            "title": task_entity.title,
            "path": str(rel_path),
        }

        if duplicates:
            result["duplicates"] = [
                {"taskId": m.task_id, "score": round(m.score, 2), "title": m.title, "state": m.state}
                for m in duplicates
            ]

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if duplicates:
                formatter.text(f"Possible duplicates ({len(duplicates)}):")
                for m in duplicates:
                    formatter.text(f"- {m.task_id}: {round(m.score, 2)} — {m.title}")
                formatter.text("")
            formatter.text(f"Created task: {task_entity.id} ({task_entity.state})\n  @{rel_path}")
            try:
                from edison.core.artifacts import format_required_fill_next_steps_for_file

                hint = format_required_fill_next_steps_for_file(task_path, display_path=str(rel_path))
                if hint:
                    # Keep stdout stable for scripts/tests that parse the created path.
                    # UX hints are still valuable, but they should not be interleaved with
                    # stdout payloads.
                    print(f"\n{hint}", file=sys.stderr)
            except Exception:
                # Fail-open: post-create UX helpers must not break task creation.
                pass

        return 0

    except Exception as e:
        formatter.error(e, error_code="create_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
