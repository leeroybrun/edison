"""
Edison task allocate_id command.

SUMMARY: Allocate next available task ID
"""

from __future__ import annotations

import argparse
import json
import sys

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
    """Allocate task ID - delegates to core library."""
    from edison.core import task

    try:
        if args.parent:
            # Allocate child ID - scan actual task files, not just metadata
            from edison.core.utils.paths import PathResolver
            from pathlib import Path

            parent_id = task.normalize_record_id("task", args.parent)

            # Look for existing child IDs in actual task directories
            project_root = PathResolver.resolve_project_root()
            tasks_root = project_root / ".project" / "tasks"

            existing_children = []
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
            # Allocate top-level ID
            # This would need a new function in core - for now use simple logic
            records = task.list_records(record_type="task")
            max_id = 0
            for record in records:
                try:
                    # Extract numeric prefix from IDs like "150-something"
                    parts = record.record_id.split("-")
                    if parts[0].isdigit():
                        max_id = max(max_id, int(parts[0]))
                except (ValueError, IndexError):
                    continue

            next_id = str(max_id + 1)
            if args.prefix:
                next_id = f"{next_id}-{args.prefix}"

        if args.json:
            print(json.dumps({
                "nextId": next_id,  # camelCase for consistency with tests
                "parent": args.parent,
                "prefix": args.prefix,
            }, indent=2))
        else:
            print(f"Next available ID: {next_id}")
            if args.parent:
                print(f"Parent: {args.parent}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, file=sys.stderr, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
