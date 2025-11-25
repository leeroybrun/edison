"""
Edison task cleanup_stale_locks command.

SUMMARY: Remove stale task locks
"""

from __future__ import annotations

import argparse
import sys
import json
import sys
import time
import sys
from pathlib import Path

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
    """Cleanup stale locks - delegates to core library."""
    from edison.core import task

    try:
        # Find all lock files in task directories
        task_root = task.TASK_ROOT
        lock_files = list(Path(task_root).rglob("*.lock"))

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
            if args.json:
                print(json.dumps({
                    "dry_run": True,
                    "stale_locks": stale_locks,
                    "count": len(stale_locks),
                    "age_threshold": args.age,
                }, indent=2))
            else:
                print(f"Found {len(stale_locks)} stale lock(s) (age > {args.age}s):")
                for lock in stale_locks:
                    print(f"  {lock['path']} (age: {lock['age_seconds']}s)")
            return 0

        # Remove stale locks
        removed = []
        for lock in stale_locks:
            try:
                Path(lock["path"]).unlink()
                removed.append(lock)
            except OSError as e:
                if not args.json:
                    print(f"Warning: Could not remove {lock['path']}: {e}")

        if args.json:
            print(json.dumps({
                "status": "cleaned",
                "removed": len(removed),
                "locks": removed,
                "ageThreshold": args.age,
            }, indent=2))
        else:
            print(f"Removed {len(removed)} stale lock(s)")
            for lock in removed:
                print(f"  {lock['path']}")

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
