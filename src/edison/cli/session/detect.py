"""
Edison session detect command.

SUMMARY: Detect the current session scope (PID/worktree/env aware)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Detect the current session scope (PID/worktree/env aware)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Optional session ID to validate/detect (defaults to auto-detection)",
    )
    parser.add_argument(
        "--owner",
        help="Optional owner name for best-effort session detection",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _path_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate = candidate.resolve()
        parent = parent.resolve()
    except Exception:
        return False
    try:
        candidate.relative_to(parent)
        return True
    except Exception:
        return False


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        from edison.core.session.core.id import detect_session_id, validate_session_id
        from edison.core.session.persistence.repository import SessionRepository
        from edison.core.config.domains.session import SessionConfig
        from edison.core.session.worktree.config_helpers import _resolve_archive_directory

        project_root = get_repo_root(args)
        detected = detect_session_id(
            explicit=getattr(args, "session_id", None),
            owner=getattr(args, "owner", None),
            project_root=project_root,
        )

        if not detected:
            payload = {
                "sessionId": None,
                "worktreePath": None,
                "archivedWorktreePath": None,
                "inWorktree": False,
                "projectRoot": str(project_root.resolve()),
                "cwd": str(Path.cwd().resolve()),
            }
            formatter.json_output(payload) if formatter.json_mode else formatter.text("No session detected.")
            return 0

        session_id = validate_session_id(detected)
        repo = SessionRepository(project_root=project_root)
        entity = repo.get(session_id)
        if not entity:
            payload = {
                "sessionId": session_id,
                "worktreePath": None,
                "archivedWorktreePath": None,
                "inWorktree": False,
                "projectRoot": str(project_root.resolve()),
                "cwd": str(Path.cwd().resolve()),
                "sessionFound": False,
            }
            formatter.json_output(payload) if formatter.json_mode else formatter.text(
                f"Detected session {session_id}, but it does not exist."
            )
            return 0

        session = entity.to_dict()
        worktree_path_raw = ((session.get("git") or {}).get("worktreePath") or "").strip()
        worktree_path = str(Path(worktree_path_raw).resolve()) if worktree_path_raw else None

        in_worktree = False
        if worktree_path:
            in_worktree = _path_within(Path.cwd(), Path(worktree_path))

        archived_worktree_path: str | None = None
        if worktree_path and not Path(worktree_path).exists():
            wt_cfg = SessionConfig(repo_root=project_root).get_worktree_config()
            archive_dir = _resolve_archive_directory(wt_cfg, project_root)
            candidate = (archive_dir / session_id).resolve()
            if candidate.exists():
                archived_worktree_path = str(candidate)

        payload = {
            "sessionId": session_id,
            "worktreePath": worktree_path,
            "archivedWorktreePath": archived_worktree_path,
            "inWorktree": in_worktree,
            "projectRoot": str(project_root.resolve()),
            "cwd": str(Path.cwd().resolve()),
            "sessionFound": True,
        }

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(f"Session: {session_id}")
            if worktree_path:
                formatter.text(f"Worktree: {worktree_path}")
            formatter.text(f"In worktree: {in_worktree}")
            if archived_worktree_path:
                formatter.text(f"Archived worktree: {archived_worktree_path}")
        return 0

    except Exception as e:
        formatter.error(e, error_code="session_detect_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))

