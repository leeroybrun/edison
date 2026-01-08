from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from edison.cli._mutability import is_mutating_invocation

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


def _extract_task_id_from_args(args: argparse.Namespace) -> str | None:
    """Best-effort extraction of a task id from common CLI argument shapes."""
    raw = getattr(args, "task_id", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    raw = getattr(args, "record_id", None)
    if isinstance(raw, str) and raw.strip():
        # Only treat record_id as task id when it is NOT a QA record.
        if raw.endswith("-qa") or raw.endswith(".qa"):
            return None
        return raw.strip()
    return None


def _infer_session_id_from_task(*, project_root: Path, task_id: str) -> str | None:
    """Infer session_id for a session-scoped task (best-effort)."""
    try:
        from edison.cli._utils import resolve_existing_task_id
        from edison.core.task.repository import TaskRepository

        resolved = resolve_existing_task_id(project_root=project_root, raw_task_id=str(task_id))
        repo = TaskRepository(project_root=project_root)
        task = repo.get(resolved)
        if not task:
            return None
        sid = getattr(task, "session_id", None)
        return str(sid) if isinstance(sid, str) and sid.strip() else None
    except Exception:
        return None


def _resolve_session_worktree_root(*, project_root: Path, session_id: str) -> Path | None:
    try:
        from edison.core.session.persistence.repository import SessionRepository

        repo = SessionRepository(project_root=project_root)
        entity = repo.get(session_id)
        if not entity:
            return None
        session = entity.to_dict() if hasattr(entity, "to_dict") else (entity if isinstance(entity, dict) else {})
        worktree_path = (session.get("git") or {}).get("worktreePath")
        if not worktree_path:
            return None
        return Path(str(worktree_path)).resolve()
    except Exception:
        return None


def maybe_warn_task_worktree_mismatch(
    *,
    project_root: Path,
    command_name: str,
    args: argparse.Namespace,
    json_mode: bool,
) -> None:
    """Warn (stderr) when running task-scoped commands outside a session worktree.

    This is intentionally warning-only: it helps prevent stale evidence/validation
    without blocking read-only inspection commands.
    """
    if json_mode:
        # Keep JSON output clean; warnings should not pollute stdout.
        pass

    # Only warn for commands that strongly depend on the session worktree state.
    if not (command_name.startswith("evidence ") or command_name.startswith("qa ")):
        return

    task_id = _extract_task_id_from_args(args)
    if not task_id:
        return

    session_id = _infer_session_id_from_task(project_root=project_root, task_id=task_id)
    if not session_id:
        return

    worktree_root = _resolve_session_worktree_root(project_root=project_root, session_id=session_id)
    if not worktree_root:
        return

    cwd = Path.cwd()
    if _path_within(cwd, worktree_root) or _path_within(project_root, worktree_root):
        return

    msg = (
        "WARNING: command is being run outside the session worktree; results may be stale/wrong.\n"
        f"Command: {command_name}\n"
        f"Task: {task_id}\n"
        f"Session: {session_id}\n"
        f"Worktree: {worktree_root}\n"
        f"Run:\n"
        f"  cd {worktree_root}\n"
        f"  export AGENTS_SESSION={session_id}\n"
        f"  export AGENTS_PROJECT_ROOT={worktree_root}\n"
    )
    print(msg, file=sys.stderr)


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
    if not is_mutating_invocation(command_name, args):
        return None

    target_raw = _extract_session_id_from_args(args) or detect_session_id(project_root=project_root)
    if not target_raw:
        task_id = _extract_task_id_from_args(args)
        if task_id:
            target_raw = _infer_session_id_from_task(project_root=project_root, task_id=task_id)
    if not target_raw:
        return None
    try:
        session_id = validate_session_id(str(target_raw))
    except Exception:
        return None

    worktree_root = _resolve_session_worktree_root(project_root=project_root, session_id=session_id)
    if not worktree_root:
        return None

    cwd = Path.cwd()
    if _path_within(cwd, worktree_root) or _path_within(project_root, worktree_root):
        return None

    archived_worktree_path: str | None = None
    try:
        if not worktree_root.exists():
            from edison.core.session.worktree.config_helpers import _resolve_archive_directory

            archive_dir = _resolve_archive_directory(wt_cfg, project_root)
            candidate = (archive_dir / session_id).resolve()
            if candidate.exists():
                archived_worktree_path = str(candidate)
    except Exception:
        archived_worktree_path = None

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
        hint = f"cd {worktree_root}"
        if archived_worktree_path:
            hint = f"edison git worktree-restore {session_id}"
        print(
            json.dumps(
                {
                    "error": "worktree_enforcement",
                    "command": command_name,
                    "sessionId": session_id,
                    "worktreePath": str(worktree_root),
                    "archivedWorktreePath": archived_worktree_path,
                    "message": "Command must run inside the session worktree.",
                    "hint": hint,
                }
            )
        )
    else:
        print(msg, file=sys.stderr)

    return 2


__all__ = ["maybe_enforce_session_worktree", "maybe_warn_task_worktree_mismatch"]
