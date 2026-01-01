"""
Edison session recovery clean_worktrees command.

SUMMARY: Clean orphaned worktrees
"""
from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Clean orphaned worktrees"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually cleaning",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Archive orphaned session worktrees",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Clean orphaned worktrees - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        project_root = Path(get_repo_root(args)).resolve()
        os.environ["AGENTS_PROJECT_ROOT"] = str(project_root)

        from edison.core.utils.git.worktree import list_worktrees
        from edison.core.session.worktree.config_helpers import _get_worktree_base, _config
        from edison.core.session.worktree.cleanup import archive_worktree
        from edison.core.session.persistence.repository import SessionRepository

        repo_dir = project_root
        base_dir = _get_worktree_base()
        cfg = _config().get_worktree_config()
        prefix = str(cfg.get("branchPrefix") or "session/")

        all_worktrees = list_worktrees(repo_root=repo_dir)
        orphans: list[dict[str, str]] = []

        for wt in all_worktrees:
            raw_path = str(wt.get("path") or "").strip()
            if not raw_path:
                continue
            wt_path = Path(raw_path).resolve()
            if wt_path == repo_dir:
                continue
            # Focus on the configured session worktree base directory.
            try:
                if not wt_path.is_relative_to(base_dir.resolve()):
                    continue
            except AttributeError:
                if not str(wt_path).startswith(str(base_dir.resolve())):
                    continue

            # Skip internal folders under base dir.
            if wt_path.name in {"_archived", "_meta"}:
                continue

            session_id = wt_path.name
            repo = SessionRepository(project_root=project_root)
            if repo.exists(session_id):
                continue

            branch = str(wt.get("branch") or "")
            if branch and not branch.startswith(prefix):
                # Not a session branch; ignore.
                continue

            orphans.append(
                {
                    "sessionId": session_id,
                    "path": str(wt_path),
                    "relativePath": str(wt_path.relative_to(project_root)),
                    "branch": branch,
                }
            )

        dry_run = bool(args.dry_run) or not bool(args.force)
        archived: list[dict[str, str]] = []
        if not dry_run:
            for o in orphans:
                sid = o["sessionId"]
                wt_path = Path(o["path"])
                archived_path = archive_worktree(sid, wt_path, dry_run=False)
                archived.append(
                    {
                        "sessionId": sid,
                        "archivedPath": str(archived_path),
                        "archivedRelativePath": str(archived_path.relative_to(project_root)),
                    }
                )

        result = {
            "dry_run": dry_run,
            "worktreeBase": str(base_dir),
            "orphans": orphans,
            "archived": archived,
            "count": len(orphans),
            "status": "completed",
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if dry_run:
                formatter.text(f"Orphaned worktrees detected: {len(orphans)}")
                for o in orphans:
                    formatter.text(f"  - {o['sessionId']}: {o['relativePath']}")
            else:
                formatter.text(f"✓ Archived {len(archived)} orphaned worktree(s)")
                for a in archived:
                    formatter.text(f"  - {a['sessionId']}: {a['archivedRelativePath']}")

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
