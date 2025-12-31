"""
Edison git worktree-restore command.

SUMMARY: Restore archived worktree
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_dry_run_flag
from edison.core.session import worktree

SUMMARY = "Restore archived worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to restore worktree for",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Override source archive path",
    )
    parser.add_argument(
        "--base-branch",
        type=str,
        help="Base branch to use (default: main)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force linking the session to the restored worktree even if session already points elsewhere",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Restore archived worktree - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        cfg = worktree._config().get_worktree_config()
        if not cfg.get("enabled", False):
            raise RuntimeError(
                "Worktrees are disabled (worktrees.enabled=false). "
                "Enable worktrees in config or use `edison session create --no-worktree`."
            )

        # Fail fast if the session already claims a different worktree.
        target_path, _ = worktree.resolve_worktree_target(args.session_id)
        from edison.core.session.persistence.repository import SessionRepository

        project_root = worktree.get_repo_dir()
        sess_repo = SessionRepository(project_root=project_root)
        session_entity = sess_repo.get(args.session_id)
        if session_entity:
            existing = (session_entity.to_dict().get("git") or {}).get("worktreePath")
            if existing:
                try:
                    if Path(str(existing)).resolve() != Path(target_path).resolve() and not args.force:
                        raise RuntimeError(
                            "Session is already linked to a different worktree. "
                            f"Existing: {existing}. Target: {target_path}. "
                            "Re-run with --force to override."
                        )
                except RuntimeError:
                    raise
                except Exception:
                    if not args.force:
                        raise RuntimeError(
                            "Session is already linked to a different worktree. "
                            f"Existing: {existing}. Target: {target_path}. "
                            "Re-run with --force to override."
                        )

        # Restore the worktree from archive
        restored_path = worktree.restore_worktree(
            session_id=args.session_id,
            source=args.source,
            base_branch=args.base_branch,
            dry_run=args.dry_run,
        )

        _, branch_name = worktree.resolve_worktree_target(args.session_id)

        session_updated = False
        if not args.dry_run and session_entity:
            from edison.core.session.core.models import Session

            base_ref = worktree.resolve_worktree_base_ref(
                repo_dir=worktree.get_repo_dir(), cfg=cfg, override=args.base_branch
            )
            data = session_entity.to_dict()
            data.setdefault("git", {})
            data["git"].update(
                worktree.prepare_session_git_metadata(
                    args.session_id,
                    restored_path,
                    branch_name,
                    base_branch=base_ref,
                )
            )
            sess_repo.save(Session.from_dict(data))
            session_updated = True

        result = {
            "session_id": args.session_id,
            "restored_path": str(restored_path),
            "branch_name": branch_name,
            "dry_run": args.dry_run,
            "session_found": bool(session_entity),
            "session_updated": session_updated,
        }

        if args.json:
            formatter.json_output(result)
        else:
            if args.dry_run:
                formatter.text(f"Would restore worktree:")
                formatter.text(f"  Session: {args.session_id}")
                formatter.text(f"  Path: {restored_path}")
                formatter.text(f"  Branch: {branch_name}")
            else:
                formatter.text(f"Restored worktree for session: {args.session_id}")
                formatter.text(f"  Path: {restored_path}")
                formatter.text(f"  Branch: {branch_name}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_restore_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
