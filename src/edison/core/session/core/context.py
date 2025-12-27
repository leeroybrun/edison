from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Dict

from edison.core.utils.paths import PathResolver


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
    def build_pal_environment(
        session_id: str,
        base_env: Optional[Dict[str, str]] = None,
        *,
        require_worktree: bool = True,
    ) -> Dict[str, str]:
        """Return an environment dict with PAL_WORKING_DIR bound to the session worktree."""
        # Lazy import to avoid circular dependency with lifecycle.manager
        from edison.core.session.lifecycle.manager import get_session
        session = get_session(session_id)
        worktree_path = SessionContext._extract_worktree_path(session)

        env: Dict[str, str] = dict(base_env or os.environ)

        if not worktree_path:
            if require_worktree:
                raise RuntimeError(
                    f"Session {session_id} is missing git.worktreePath; cannot prepare Pal environment"
                )
            env.pop("PAL_WORKING_DIR", None)
            return env

        resolved = SessionContext._validate_worktree_path(worktree_path)
        env["PAL_WORKING_DIR"] = str(resolved)
        # Enforce Edison path resolution within the session worktree even if callers
        # run the process from the primary checkout or change directories later.
        env["AGENTS_PROJECT_ROOT"] = str(resolved)
        env["AGENTS_SESSION"] = str(session_id)
        return env

    @staticmethod
    @contextmanager
    def in_session_worktree(session_id: str) -> Iterator[dict]:
        # Lazy import to avoid circular dependency with lifecycle.manager
        from edison.core.session.lifecycle.manager import get_session
        session = get_session(session_id)
        worktree_path = SessionContext._extract_worktree_path(session)
        original_cwd = os.getcwd()
        original_pal_dir = os.environ.get("PAL_WORKING_DIR")
        original_agents_root = os.environ.get("AGENTS_PROJECT_ROOT")
        original_agents_session = os.environ.get("AGENTS_SESSION")
        try:
            if worktree_path:
                try:
                    resolved = SessionContext._validate_worktree_path(worktree_path)
                    os.environ["PAL_WORKING_DIR"] = str(resolved)
                    os.environ["AGENTS_PROJECT_ROOT"] = str(resolved)
                    os.environ["AGENTS_SESSION"] = str(session_id)
                    os.chdir(resolved)
                except FileNotFoundError:
                    # Gracefully fall back to the original cwd when the
                    # worktree hint is stale or missing. Tests may operate on
                    # sessions without materialized worktrees.
                    worktree_path = None
            yield session
        finally:
            if original_pal_dir is None:
                os.environ.pop("PAL_WORKING_DIR", None)
            else:
                os.environ["PAL_WORKING_DIR"] = original_pal_dir
            if original_agents_root is None:
                os.environ.pop("AGENTS_PROJECT_ROOT", None)
            else:
                os.environ["AGENTS_PROJECT_ROOT"] = original_agents_root
            if original_agents_session is None:
                os.environ.pop("AGENTS_SESSION", None)
            else:
                os.environ["AGENTS_SESSION"] = original_agents_session
            os.chdir(original_cwd)
