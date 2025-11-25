from __future__ import annotations

"""Helpers for formatting Zen MCP clink invocations with worktree awareness."""

import os
import shlex
from pathlib import Path
from typing import Dict, Optional

from edison.core.session.context import SessionContext
from edison.core.utils import git as git_utils


TOOL_NAME = "mcp__edison-zen__clink"


def resolve_working_directory(
    session_id: Optional[str] = None,
    *,
    start_path: Optional[Path | str] = None,
) -> Optional[Path]:
    """
    Return the worktree path for the active session or current checkout.

    Resolution order:
    1. Session worktree via SessionContext (validated, no duplication).
    2. Current path if it is a linked worktree (git-utils detection).
    """
    if session_id:
        try:
            env = SessionContext.build_zen_environment(
                session_id,
                base_env=os.environ.copy(),
                require_worktree=False,
            )
            zen_dir = env.get("ZEN_WORKING_DIR")
            if zen_dir:
                return Path(zen_dir).expanduser().resolve()
        except Exception:
            # Fall through to git-based detection when session metadata is incomplete.
            pass

    try:
        probe_path = Path(start_path) if start_path is not None else Path.cwd()
        if git_utils.is_worktree(probe_path):
            return git_utils.get_repo_root(probe_path)
    except Exception:
        return None

    return None


def format_clink_cli_command(
    *,
    cli_name: str,
    role: Optional[str] = None,
    prompt: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_name: str = TOOL_NAME,
    extra_args: Optional[Dict[str, str]] = None,
) -> str:
    """
    Return a CLI-style clink invocation string with optional worktree binding.

    Examples:
        mcp__edison-zen__clink --cli_name codex --role default --prompt '...' --working_directory /abs/path
    """
    parts = [tool_name, f"--cli_name {shlex.quote(cli_name)}"]
    if role:
        parts.append(f"--role {shlex.quote(role)}")
    if prompt:
        parts.append(f"--prompt {shlex.quote(prompt)}")

    worktree = resolve_working_directory(session_id=session_id)
    if worktree:
        parts.append(f"--working_directory {shlex.quote(str(worktree))}")

    if extra_args:
        for key, value in extra_args.items():
            parts.append(f"--{key} {shlex.quote(str(value))}")

    return " ".join(parts)


__all__ = ["TOOL_NAME", "resolve_working_directory", "format_clink_cli_command"]
