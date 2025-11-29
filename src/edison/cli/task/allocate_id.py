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
        "--base",  # Alias for backwards compatibility with tests
        dest="parent",
        help="Parent task ID for child allocation (e.g., 150-wave1 or 201)",
    )
    parser.add_argument(
        "--prefix",
        help="ID prefix (overrides parent-based prefix)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Allocate task ID - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.task import TaskRepository, normalize_record_id

    try:
        # Resolve project root
        project_root = get_repo_root(args)
        repo = TaskRepository(project_root=project_root)

        if args.parent:
            # Allocate child ID - scan actual task files
            parent_id = normalize_record_id("task", args.parent)

            # Look for existing child IDs in actual task directories
            from edison.core.config.domains import TaskConfig
            config = TaskConfig(repo_root=project_root)
            tasks_root = config.tasks_root()

            existing_children = []
            if tasks_root.exists():
                for state_dir in tasks_root.iterdir():
                    if state_dir.is_dir():
                        # Match files like "201.1-something.md" or "201-1-something.md"
                        for task_file in state_dir.glob(f"{parent_id}.*"):
                            if task_file.suffix == ".md":
                                # Extract child number from "201.1" or "201-1"
                                name_part = task_file.stem.split("-")[0]  # Get "201.1" part
                                if "." in name_part:
                                    try:
                                        child_num = int(name_part.split(".")[-1])
                                        existing_children.append(child_num)
                                    except ValueError:
                                        pass

            # Determine next child number
            if existing_children:
                next_child_num = max(existing_children) + 1
            else:
                next_child_num = 1

            next_id = f"{parent_id}.{next_child_num}"

            # If prefix is provided, add it after the child number
            if args.prefix:
                next_id = f"{next_id}-{args.prefix}"
        else:
            # Allocate top-level ID using TaskRepository
            tasks = repo.get_all()
            max_id = 0
            for task_entity in tasks:
                try:
                    # Extract numeric prefix from IDs like "150-something"
                    parts = task_entity.id.split("-")
                    if parts[0].isdigit():
                        max_id = max(max_id, int(parts[0]))
                except (ValueError, IndexError):
                    continue

            next_id = str(max_id + 1)
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
