from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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


def _extract_session_id_from_args(args: argparse.Namespace) -> str | None:
    raw = getattr(args, "session", None)
    if raw:
        return str(raw)
    raw = getattr(args, "session_id", None)
    if raw:
        return str(raw)
    return None


def _is_mutating_invocation(command_name: str, args: argparse.Namespace) -> bool:
    # Keep this minimal and conservative: only enforce for known mutating flags.
    if command_name == "qa validate":
        return bool(getattr(args, "execute", False) or getattr(args, "check_only", False))
    return True


def maybe_enforce_session_worktree(
    *,
    project_root: Path,
    command_name: str,
    args: argparse.Namespace,
    json_mode: bool,
) -> int | None:
    """Return an exit code when enforcement blocks the command, else None.

    NOTE: This is shared between the dispatcher and direct module entrypoints
    used in tests. The dispatcher remains the canonical entrypoint for `edison`.
    """
    try:
        from edison.core.config.domains.session import SessionConfig
        from edison.core.session.core.id import detect_session_id, validate_session_id
        from edison.core.session.persistence.repository import SessionRepository
    except Exception:
        return None

    try:
        wt_cfg = SessionConfig(repo_root=project_root).get_worktree_config()
    except Exception:
        return None

    if not bool(wt_cfg.get("enabled", True)):
        return None

    enforcement = wt_cfg.get("enforcement") or {}
    if not isinstance(enforcement, dict) or not bool(enforcement.get("enabled", False)):
        return None

    commands = enforcement.get("commands") or []
    if not isinstance(commands, list) or not commands:
        return None
    if command_name not in commands and "*" not in commands:
        return None

    # Allow read-only invocations from the primary checkout.
    if not _is_mutating_invocation(command_name, args):
        return None

    target_raw = _extract_session_id_from_args(args) or detect_session_id(project_root=project_root)
    if not target_raw:
        return None
    try:
        session_id = validate_session_id(str(target_raw))
    except Exception:
        return None

    try:
        repo = SessionRepository(project_root=project_root)
        entity = repo.get(session_id)
        if not entity:
            return None
        session = entity.to_dict() if hasattr(entity, "to_dict") else (entity if isinstance(entity, dict) else {})
        worktree_path = (session.get("git") or {}).get("worktreePath")
        if not worktree_path:
            return None
        worktree_root = Path(str(worktree_path)).resolve()
    except Exception:
        return None

    cwd = Path.cwd()
    if _path_within(cwd, worktree_root) or _path_within(project_root, worktree_root):
        return None

    msg = (
        "WORKTREE ENFORCEMENT: this command must run inside the session worktree.\n"
        f"Command: {command_name}\n"
        f"Session: {session_id}\n"
        f"Worktree: {worktree_root}\n"
        f"Run:\n"
        f"  cd {worktree_root}\n"
        f"  export AGENTS_SESSION={session_id}\n"
        f"  export AGENTS_PROJECT_ROOT={worktree_root}\n"
    )

    if json_mode:
        print(
            json.dumps(
                {
                    "error": "worktree_enforcement",
                    "command": command_name,
                    "sessionId": session_id,
                    "worktreePath": str(worktree_root),
                    "message": "Command must run inside the session worktree.",
                    "hint": f"cd {worktree_root}",
                }
            )
        )
    else:
        print(msg, file=sys.stderr)

    return 2


__all__ = ["maybe_enforce_session_worktree"]
