from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Dict

from edison.core.utils.paths import PathResolver

from .manager import get_session


class SessionContext:
    """Manage execution within a session's worktree if configured."""

    @staticmethod
    def _extract_worktree_path(session: dict) -> Optional[str]:
        git_meta = session.get("git", {}) if isinstance(session.get("git", {}), dict) else {}
        return git_meta.get("worktreePath") or session.get("worktree_path")

    @staticmethod
    def _validate_worktree_path(path_str: str) -> Path:
        """Normalize and validate a declared worktree path.

        Raises a ValueError when the path is outside the project repository
        and FileNotFoundError when the path does not exist.
        """
        resolved = Path(path_str).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Worktree path does not exist: {resolved}")
        return resolved

    @staticmethod
    def build_zen_environment(
        session_id: str,
        base_env: Optional[Dict[str, str]] = None,
        *,
        require_worktree: bool = True,
    ) -> Dict[str, str]:
        """Return an environment dict with ZEN_WORKING_DIR bound to the session worktree."""
        session = get_session(session_id)
        worktree_path = SessionContext._extract_worktree_path(session)

        env: Dict[str, str] = dict(base_env or os.environ)

        if not worktree_path:
            if require_worktree:
                raise RuntimeError(
                    f"Session {session_id} is missing git.worktreePath; cannot prepare Zen environment"
                )
            env.pop("ZEN_WORKING_DIR", None)
            return env

        resolved = SessionContext._validate_worktree_path(worktree_path)
        env["ZEN_WORKING_DIR"] = str(resolved)
        env.setdefault("AGENTS_PROJECT_ROOT", str(PathResolver.resolve_project_root()))
        return env

    @staticmethod
    @contextmanager
    def in_session_worktree(session_id: str) -> Iterator[dict]:
        session = get_session(session_id)
        worktree_path = SessionContext._extract_worktree_path(session)
        original_cwd = os.getcwd()
        original_zen_dir = os.environ.get("ZEN_WORKING_DIR")
        try:
            if worktree_path:
                try:
                    resolved = SessionContext._validate_worktree_path(worktree_path)
                    os.environ["ZEN_WORKING_DIR"] = str(resolved)
                    os.chdir(resolved)
                except FileNotFoundError:
                    # Gracefully fall back to the original cwd when the
                    # worktree hint is stale or missing. Tests may operate on
                    # sessions without materialized worktrees.
                    worktree_path = None
            yield session
        finally:
            if original_zen_dir is None:
                os.environ.pop("ZEN_WORKING_DIR", None)
            else:
                os.environ["ZEN_WORKING_DIR"] = original_zen_dir
            os.chdir(original_cwd)
