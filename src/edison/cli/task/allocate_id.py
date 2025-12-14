"""
Edison task allocate_id command.

SUMMARY: Allocate next available task ID
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Allocate next available task ID"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--parent",
        help="Parent task ID for child allocation (e.g., 150-wave1 or 201)",
    )
    parser.add_argument(
        "--prefix",
        help="ID prefix (overrides parent-based prefix)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Allocate task ID - delegates to TaskRepository for ID generation."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Import lazily to keep CLI startup fast.
        from edison.core.task import TaskRepository, normalize_record_id

        # Resolve project root
        project_root = get_repo_root(args)
        repo = TaskRepository(project_root=project_root)

        if args.parent:
            # Allocate child ID using repository (scans task files)
            parent_id = normalize_record_id("task", args.parent)
            next_id = repo.get_next_child_id(parent_id)

            # If prefix is provided, add it after the child number
            if args.prefix:
                next_id = f"{next_id}-{args.prefix}"
        else:
            # Allocate top-level ID using TaskRepository
            next_num = repo.get_next_top_level_id()
            next_id = str(next_num)
            if args.prefix:
                next_id = f"{next_id}-{args.prefix}"

        formatter.json_output({
            "nextId": next_id,  # camelCase for consistency with tests
            "parent": args.parent,
            "prefix": args.prefix,
        }) if formatter.json_mode else formatter.text(
            f"Next available ID: {next_id}" +
            (f"\nParent: {args.parent}" if args.parent else "")
        )

        return 0

    except Exception as e:
        formatter.error(e, error_code="allocate_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
