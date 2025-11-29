"""
Edison task cleanup_stale_locks command.

SUMMARY: Remove stale task locks
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.config.domains import TaskConfig

SUMMARY = "Remove stale task locks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--max-age",
        "--age",  # Backwards compatibility
        dest="age",
        type=int,
        default=3600,
        help="Max age in seconds for locks to be considered stale (default: 3600)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup without removing locks",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Cleanup stale locks - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Get task root from config
        config = TaskConfig(repo_root=project_root)
        task_root = config.tasks_root()

        # Find all lock files in task directories
        lock_files = list(task_root.rglob("*.lock")) if task_root.exists() else []

        current_time = time.time()
        stale_locks = []

        for lock_file in lock_files:
            try:
                # Check if lock is stale
                lock_age = current_time - lock_file.stat().st_mtime
                if lock_age > args.age:
                    stale_locks.append({
                        "path": str(lock_file),
                        "age_seconds": int(lock_age),
                    })
            except OSError:
                continue

        if args.dry_run:
            formatter.json_output({
                "dry_run": True,
                "stale_locks": stale_locks,
                "count": len(stale_locks),
                "age_threshold": args.age,
            }) if formatter.json_mode else formatter.text(
                f"Found {len(stale_locks)} stale lock(s) (age > {args.age}s):\n" +
                "\n".join(f"  {lock['path']} (age: {lock['age_seconds']}s)" for lock in stale_locks)
            )
            return 0

        # Remove stale locks
        removed = []
        for lock in stale_locks:
            try:
                Path(lock["path"]).unlink()
                removed.append(lock)
            except OSError as e:
                if not formatter.json_mode:
                    formatter.text(f"Warning: Could not remove {lock['path']}: {e}")

        formatter.json_output({
            "status": "cleaned",
            "removed": len(removed),
            "locks": removed,
            "ageThreshold": args.age,
        }) if formatter.json_mode else formatter.text(
            f"Removed {len(removed)} stale lock(s)\n" +
            "\n".join(f"  {lock['path']}" for lock in removed)
        )

        return 0

    except Exception as e:
        formatter.error(e, error_code="cleanup_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
