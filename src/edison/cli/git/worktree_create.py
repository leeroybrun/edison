"""
Edison git worktree-create command.

SUMMARY: Create git worktree for session
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_dry_run_flag, resolve_session_id
from edison.core.session import worktree

SUMMARY = "Create git worktree for session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        type=str,
        help="Session ID to create worktree for (defaults to current session when omitted)",
    )
    parser.add_argument(
        "--branch",
        type=str,
        help="Base ref to branch from (overrides config; default: current primary HEAD unless baseBranch is configured or baseBranchMode=fixed)",
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Override worktree path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force linking the session to the created/restored worktree even if session already points elsewhere",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies after creation",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create git worktree - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        project_root = worktree.get_repo_dir()
        session_id_raw = str(args.session_id) if getattr(args, "session_id", None) else None
        if session_id_raw is None:
            session_id_raw = resolve_session_id(
                project_root=project_root,
                explicit=None,
                required=True,
            )
        from edison.core.session.core.id import validate_session_id

        session_id = validate_session_id(str(session_id_raw))

        cfg = worktree._config().get_worktree_config()
        if not cfg.get("enabled", False):
            raise RuntimeError(
                "Worktrees are disabled (worktrees.enabled=false). "
                "Enable worktrees in config or use `edison session create --no-worktree`."
            )
        base_ref = worktree.resolve_worktree_base_ref(
            repo_dir=worktree.get_repo_dir(), cfg=cfg, override=args.branch
        )

        # Fail fast if the session already claims a different worktree.
        worktree_path_preview, branch_name_preview = worktree.create_worktree(
            session_id=session_id,
            base_branch=args.branch,
            worktree_path_override=args.path,
            install_deps=args.install_deps if args.install_deps else None,
            dry_run=True,
        )
        if worktree_path_preview is None or branch_name_preview is None:
            raise RuntimeError("Failed to compute worktree target (unexpected null path/branch)")

        session_updated = False
        session_found = False

        from edison.core.session.persistence.repository import SessionRepository

        sess_repo = SessionRepository(project_root=project_root)
        session_entity = sess_repo.get(session_id)
        if session_entity:
            session_found = True
            existing = (session_entity.to_dict().get("git") or {}).get("worktreePath")
            if existing:
                try:
                    if Path(str(existing)).resolve() != Path(worktree_path_preview).resolve() and not args.force:
                        raise RuntimeError(
                            "Session is already linked to a different worktree. "
                            f"Existing: {existing}. Target: {worktree_path_preview}. "
                            "Re-run with --force to override."
                        )
                except RuntimeError:
                    raise
                except Exception:
                    if not args.force:
                        raise RuntimeError(
                            "Session is already linked to a different worktree. "
                            f"Existing: {existing}. Target: {worktree_path_preview}. "
                            "Re-run with --force to override."
                        )

        worktree_path, branch_name = worktree.create_worktree(
            session_id=session_id,
            base_branch=args.branch,
            worktree_path_override=args.path,
            install_deps=args.install_deps if args.install_deps else None,
            dry_run=args.dry_run,
        )

        # Persist git metadata back into the session record (when it exists).
        if not args.dry_run and worktree_path and branch_name and session_entity:
            from edison.core.session.core.models import Session

            if session_entity:
                data = session_entity.to_dict()
                data.setdefault("git", {})
                data["git"].update(
                    worktree.prepare_session_git_metadata(
                        session_id,
                        worktree_path,
                        branch_name,
                        base_branch=base_ref,
                    )
                )
                sess_repo.save(Session.from_dict(data))
                session_updated = True

        result = {
            "session_id": session_id,
            "worktree_path": str(worktree_path) if worktree_path else None,
            "branch_name": branch_name,
            "base_ref": base_ref,
            "base_branch_mode": cfg.get("baseBranchMode"),
            "dry_run": args.dry_run,
            "session_found": session_found,
            "session_updated": session_updated,
        }

        if args.json:
            formatter.json_output(result)
        else:
            if args.dry_run:
                formatter.text(f"Would create worktree:")
                formatter.text(f"  Path: {worktree_path}")
                formatter.text(f"  Branch: {branch_name}")
                formatter.text(f"  Base: {base_ref} ({cfg.get('baseBranchMode') or 'current'})")
            else:
                formatter.text(f"Created worktree for session: {session_id}")
                formatter.text(f"  Path: {worktree_path}")
                formatter.text(f"  Branch: {branch_name}")
                formatter.text(f"  Base: {base_ref} ({cfg.get('baseBranchMode') or 'current'})")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_create_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
