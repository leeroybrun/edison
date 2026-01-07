"""
Edison session recovery clear_locks command.

SUMMARY: Clear stale locks
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.utils.io.stale_locks import cleanup_stale_locks
from edison.core.utils.locks.discovery import discover_project_lock_files

SUMMARY = "Clear stale locks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session-id",
        type=str,
        help="Clear locks for specific session",
    )
    parser.add_argument(
        "--max-age",
        "--age",
        dest="max_age",
        type=int,
        default=60,
        help="Max age in minutes for locks to be considered stale (default: 60)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup without removing locks (default when --force not set)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove stale locks",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Clear stale locks - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Honor --repo-root for underlying path resolution (PathResolver).
        repo_root = get_repo_root(args)
        os.environ["AGENTS_PROJECT_ROOT"] = str(repo_root)

        from edison.core.utils.paths import get_management_paths

        management_root = get_management_paths(Path(repo_root)).get_management_root()
        lock_files: list[Path] = []
        # Legacy: any leftover sidecar locks inside management (.project).
        lock_files.extend(list(management_root.rglob("*.lock")) if management_root.exists() else [])
        # Edison-managed locks inside `.edison/_locks/**`.
        lock_files.extend(discover_project_lock_files(repo_root=Path(repo_root)))
        lock_files = sorted(set(lock_files), key=lambda p: str(p))

        # Safe default: dry-run unless explicitly forced.
        dry_run = bool(args.dry_run) or not bool(args.force)

        if args.session_id:
            sid = str(args.session_id).strip()
            lock_files = [p for p in lock_files if sid in str(p)]

        stale, removed = cleanup_stale_locks(
            lock_files,
            max_age_seconds=int(args.max_age) * 60,
            dry_run=dry_run,
        )

        def _rel(p: Path) -> str:
            try:
                return str(p.resolve().relative_to(Path(repo_root).resolve()))
            except Exception:
                return str(p)

        result = {
            "dry_run": dry_run,
            "stale_locks": [
                {"path": str(s.path), "relativePath": _rel(s.path), "age_seconds": s.age_seconds, "pid": s.pid}
                for s in stale
            ],
            "removed": [{"path": str(p), "relativePath": _rel(p)} for p in removed],
            "count": len(removed) if not dry_run else len(stale),
            "status": "completed",
            "maxAgeMinutes": int(args.max_age),
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if dry_run:
                formatter.text(f"Stale lock(s) found: {len(stale)} (age > {int(args.max_age)}m)")
                for s in stale:
                    formatter.text(f"  - {_rel(s.path)}")
            else:
                formatter.text(f"Cleared {len(removed)} stale lock(s)")
                for p in removed:
                    formatter.text(f"  - {_rel(p)}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
