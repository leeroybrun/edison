"""
Edison task new command.

SUMMARY: Create a new task file using the project template
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

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
        dest="session_id",
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
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Create new task - delegates to core library."""
    from edison.core import task

    try:
        # Build task ID from components
        parts = [args.task_id]
        if args.wave:
            parts.append(args.wave)
        parts.append(args.slug)
        task_id = "-".join(parts)

        # Build title from type and slug
        task_type = args.task_type or "feature"
        title = f"{task_type.capitalize()}: {args.slug.replace('-', ' ')}"

        # Create the task using the actual function signature
        # Signature: create_task(task_id: str, title: str, description: str = "") -> Path
        description = ""
        if args.owner:
            description += f"Owner: {args.owner}\n"
        if args.parent:
            description += f"Parent: {args.parent}\n"
        if args.session_id:
            description += f"Session: {args.session_id}\n"
        if args.continuation_id:
            description += f"Continuation ID: {args.continuation_id}\n"

        result = task.create_task(
            task_id=task_id,
            title=title,
            description=description.strip(),
        )

        if args.json:
            print(json.dumps({
                "status": "created",
                "task_id": task_id,
                "path": str(result) if result else None,
                "title": title,
            }, indent=2, default=str))
        else:
            print(str(result))

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
