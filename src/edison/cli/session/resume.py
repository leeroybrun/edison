"""
Edison session resume command.

SUMMARY: Resume a session (prints env guidance, optionally sets .session-id)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Resume a session (prints env guidance, optionally sets .session-id)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier to resume",
    )
    parser.add_argument(
        "--set-file",
        action="store_true",
        dest="set_file",
        help="Write .session-id file in worktree (requires worktree context)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _get_session_info(session_id: str, project_root: Path) -> Dict[str, Any]:
    """Get session information for resume output.

    Args:
        session_id: Session ID to get info for
        project_root: Project root path

    Returns:
        Dict with session info

    Raises:
        ValueError: If session not found
    """
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=project_root)
    session = repo.get(session_id)

    if session is None:
        raise ValueError(f"Session not found: {session_id}")

    # Access worktree_path from GitInfo dataclass
    worktree_path = session.git.worktree_path if session.git else None

    return {
        "session_id": session_id,
        "state": session.state,
        "worktreePath": worktree_path,
        "exportCommand": f"export AGENTS_SESSION={session_id}",
    }


def _write_session_id_file(session_id: str, project_root: Path) -> Optional[Path]:
    """Write .session-id file in worktree management directory.

    Args:
        session_id: Session ID to write
        project_root: Project root path

    Returns:
        Path to the written file, or None if not in worktree
    """
    from edison.core.utils.git.worktree import is_worktree
    from edison.core.utils.paths import get_management_paths

    if not is_worktree():
        return None

    mgmt = get_management_paths(project_root)
    session_id_file = mgmt.get_management_root() / ".session-id"
    session_id_file.parent.mkdir(parents=True, exist_ok=True)
    session_id_file.write_text(session_id + "\n", encoding="utf-8")
    return session_id_file


def main(args: argparse.Namespace) -> int:
    """Resume a session - validates session exists and provides guidance."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        session_id = str(args.session_id)

        # Validate and get session info
        session_info = _get_session_info(session_id, project_root)

        # Optionally write .session-id file
        session_id_file_path: Optional[str] = None
        if getattr(args, "set_file", False):
            written_path = _write_session_id_file(session_id, project_root)
            if written_path:
                session_id_file_path = str(written_path)

        if formatter.json_mode:
            payload = {
                **session_info,
                "resumed": True,
            }
            if session_id_file_path:
                payload["sessionIdFilePath"] = session_id_file_path
            formatter.json_output(payload)
        else:
            formatter.text(f"Session: {session_id}")
            formatter.text(f"State: {session_info['state']}")

            if session_info.get("worktreePath"):
                formatter.text(f"Worktree: {session_info['worktreePath']}")
                formatter.text("")
                formatter.text("To resume in the worktree:")
                formatter.text(f"  cd {session_info['worktreePath']}")
            else:
                formatter.text("")
                formatter.text("To resume this session, set the environment variable:")
                formatter.text(f"  {session_info['exportCommand']}")

            if session_id_file_path:
                formatter.text("")
                formatter.text(f"Session ID file written: {session_id_file_path}")

            formatter.text("")
            formatter.text("Or run commands with --session flag:")
            formatter.text(f"  edison task list --session {session_id}")

        return 0

    except ValueError as e:
        formatter.error(e, error_code="session_not_found")
        return 1
    except Exception as e:
        formatter.error(e, error_code="resume_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
