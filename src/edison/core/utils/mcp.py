from __future__ import annotations

"""Helpers for formatting Pal MCP clink invocations with worktree awareness."""

import os
import shlex
from pathlib import Path
from typing import Dict, Optional

from edison.core.session.core.context import SessionContext
from edison.core.utils import git as git_utils


_TOOL_NAME_CACHE: str | None = None


def get_tool_name() -> str:
    """Load MCP tool name from configuration.

    Returns:
        str: The MCP tool name for edison-pal clink

    Raises:
        RuntimeError: If config cannot be loaded or tool name is missing
    """
    global _TOOL_NAME_CACHE
    if _TOOL_NAME_CACHE is not None:
        return _TOOL_NAME_CACHE

    try:
        from edison.core.config import ConfigManager
        from edison.core.utils.paths import resolve_project_root

        repo_root = resolve_project_root()
        cfg_manager = ConfigManager(repo_root)
        full_config = cfg_manager.load_config(validate=False)

        if "mcp" not in full_config:
            raise RuntimeError(
                "mcp configuration section is missing. "
                "Add 'mcp' section to your YAML config."
            )

        if "tool_names" not in full_config["mcp"]:
            raise RuntimeError(
                "mcp.tool_names configuration is missing. "
                "Add 'mcp.tool_names' section to your YAML config."
            )

        tool_name = full_config["mcp"]["tool_names"].get("edison_pal_clink")
        if not tool_name:
            raise RuntimeError(
                "mcp.tool_names.edison_pal_clink is not configured. "
                "Add 'mcp.tool_names.edison_pal_clink' to your YAML config."
            )

        _TOOL_NAME_CACHE = str(tool_name)
        return _TOOL_NAME_CACHE
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to load MCP tool name configuration: {e}"
        ) from e


# Lazy module-level attribute access
def __getattr__(name: str):
    if name == "TOOL_NAME":
        return get_tool_name()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
            env = SessionContext.build_pal_environment(
                session_id,
                base_env=os.environ.copy(),
                require_worktree=False,
            )
            pal_dir = env.get("PAL_WORKING_DIR")
            if pal_dir:
                return Path(pal_dir).expanduser().resolve()
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
    tool_name: str | None = None,
    extra_args: Optional[Dict[str, str]] = None,
) -> str:
    """
    Return a CLI-style clink invocation string with optional worktree binding.

    Examples:
        mcp__edison-pal__clink --cli_name codex --role default --prompt '...' --working_directory /abs/path
    """
    if tool_name is None:
        tool_name = get_tool_name()
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


__all__ = ["TOOL_NAME", "get_tool_name", "resolve_working_directory", "format_clink_cli_command"]
