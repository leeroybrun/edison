"""
Edison task cleanup_stale_locks command.

SUMMARY: Remove stale task locks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.config.domains import TaskConfig
from edison.core.utils.io.stale_locks import cleanup_stale_locks

SUMMARY = "Remove stale task locks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--max-age",
        "--age",  # Backwards compatibility
        dest="age",
        type=int,
        default=60,
        help="Max age in minutes for locks to be considered stale (default: 60)",
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

        stale, removed = cleanup_stale_locks(
            lock_files,
            max_age_seconds=int(args.age) * 60,
            dry_run=bool(args.dry_run),
        )

        def _rel(p: Path) -> str:
            try:
                return str(p.resolve().relative_to(project_root.resolve()))
            except Exception:
                return str(p)

        if args.dry_run:
            formatter.json_output({
                "dry_run": True,
                "stale_locks": [
                    {"path": str(s.path), "relativePath": _rel(s.path), "age_seconds": s.age_seconds, "pid": s.pid}
                    for s in stale
                ],
                "count": len(stale),
                "age_threshold_minutes": int(args.age),
            }) if formatter.json_mode else formatter.text(
                f"Found {len(stale)} stale lock(s) (age > {int(args.age)}m):\n"
                + "\n".join(f"  {_rel(s.path)} (age: {s.age_seconds}s)" for s in stale)
            )
            return 0

        formatter.json_output({
            "status": "cleaned",
            "removed": len(removed),
            "locks": [{"path": str(p), "relativePath": _rel(p)} for p in removed],
            "ageThresholdMinutes": int(args.age),
        }) if formatter.json_mode else formatter.text(
            f"Removed {len(removed)} stale lock(s)\n"
            + "\n".join(f"  {_rel(p)}" for p in removed)
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
