"""Zen MCP helpers scoped to Edison sessions.

This module centralises per-session Zen server launch so that each session
runs its own server bound to the correct git worktree. It intentionally
avoids mocks and relies on the real ``scripts/zen/run-server.sh`` launcher.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Sequence

from edison.core.paths.resolver import PathResolver

from .context import SessionContext


def launch_session_server(
    session_id: str,
    *,
    args: Optional[Sequence[str]] = None,
    base_env: Optional[Dict[str, str]] = None,
) -> subprocess.Popen:
    """Start a Zen MCP server bound to the session's worktree.

    Parameters
    ----------
    session_id:
        Session identifier containing ``git.worktreePath`` metadata.
    args:
        Additional arguments forwarded to ``run-server.sh``.
    base_env:
        Environment baseline to merge (defaults to ``os.environ``).

    Returns
    -------
    subprocess.Popen
        Handle to the launched server process.
    """
    env = SessionContext.build_zen_environment(session_id, base_env=base_env)
    repo_root = PathResolver.resolve_project_root()
    launcher = repo_root / "scripts" / "zen" / "run-server.sh"
    if not launcher.exists():
        raise FileNotFoundError(f"Zen launcher not found: {launcher}")

    cmd = [str(launcher), *[str(a) for a in (args or [])]]
    return subprocess.Popen(cmd, cwd=repo_root, env=env)


__all__ = ["launch_session_server"]
