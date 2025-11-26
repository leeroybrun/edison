"""Utility helpers for Edison core."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Union

from .cli_arguments import (
    parse_common_args,
    session_parent,
    dry_run_parent,
)
from .cli_output import (
    output_json,
    output_table,
    confirm,
    error,
    success,
)
from .time import utc_now, utc_timestamp, parse_iso8601
from .subprocess import (
    run_with_timeout,
    configured_timeout,
    check_output_with_timeout,
    reset_subprocess_timeout_cache,
    run_command,
    run_git_command,
    run_db_command,
    run_ci_command_from_string,
    expand_shell_pipeline,
)
from .text import (
    dry_duplicate_report,
    render_conditional_includes,
    ENGINE_VERSION,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)


# Lazily import git helpers to avoid circular dependency with paths/resolver at
# module import time. Git helpers depend on PathResolver from edison.core.paths,
# which itself imports subprocess helpers from this package.
def get_repo_root(start_path: Optional[Union[Path, str]] = None):
    from .git import get_repo_root as _get_repo_root

    return _get_repo_root(start_path)


def get_current_branch(start_path: Optional[Union[Path, str]] = None) -> str:
    from .git import get_current_branch as _get_current_branch

    return _get_current_branch(start_path)


def is_clean_working_tree(start_path: Optional[Union[Path, str]] = None) -> bool:
    from .git import is_clean_working_tree as _is_clean_working_tree

    return _is_clean_working_tree(start_path)


def is_worktree(start_path: Optional[Union[Path, str]] = None) -> bool:
    from .git import is_worktree as _is_worktree

    return _is_worktree(start_path)


def get_worktree_parent(start_path: Optional[Union[Path, str]] = None):
    from .git import get_worktree_parent as _get_worktree_parent

    return _get_worktree_parent(start_path)


def read_json(file_path):
    from .json_io import read_json as _read_json

    return _read_json(file_path)


def write_json_atomic(file_path, data, *, acquire_lock: bool = True) -> None:
    from .json_io import write_json_atomic as _write_json_atomic

    return _write_json_atomic(file_path, data, acquire_lock=acquire_lock)


def update_json(file_path, update_fn):
    from .json_io import update_json as _update_json

    return _update_json(file_path, update_fn)


# Lazily import MCP helpers to avoid circular imports through SessionContext
# and PathResolver during package import.
MCP_TOOL_NAME = "mcp__edison-zen__clink"


def resolve_working_directory(session_id: Optional[str] = None, *, start_path: Optional[Path | str] = None):
    from . import mcp as _mcp

    return _mcp.resolve_working_directory(session_id=session_id, start_path=start_path)


def format_clink_cli_command(
    *,
    cli_name: str,
    role: Optional[str] = None,
    prompt: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_name: str = MCP_TOOL_NAME,
    extra_args: Optional[dict] = None,
) -> str:
    from . import mcp as _mcp

    return _mcp.format_clink_cli_command(
        cli_name=cli_name,
        role=role,
        prompt=prompt,
        session_id=session_id,
        tool_name=tool_name,
        extra_args=extra_args,
    )


def get_mcp_tool_name() -> str:
    try:
        from . import mcp as _mcp

        return getattr(_mcp, "TOOL_NAME", MCP_TOOL_NAME)
    except Exception:
        return MCP_TOOL_NAME

# NOTE: dependencies module is NOT imported here to avoid import-time coupling
# Import directly: from edison.core.utils.dependencies import detect_uvx, detect_zen_mcp_server

__all__ = [
    "parse_common_args",
    "session_parent",
    "dry_run_parent",
    "output_json",
    "output_table",
    "confirm",
    "error",
    "success",
    "get_repo_root",
    "get_current_branch",
    "is_clean_working_tree",
    "is_worktree",
    "get_worktree_parent",
    "MCP_TOOL_NAME",
    "get_mcp_tool_name",
    "resolve_working_directory",
    "format_clink_cli_command",
    "utc_now",
    "utc_timestamp",
    "parse_iso8601",
    "read_json",
    "write_json_atomic",
    "update_json",
    "run_with_timeout",
    "configured_timeout",
    "check_output_with_timeout",
    "reset_subprocess_timeout_cache",
    "run_command",
    "run_git_command",
    "run_db_command",
    "run_ci_command_from_string",
    "expand_shell_pipeline",
    "dry_duplicate_report",
    "render_conditional_includes",
    "ENGINE_VERSION",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
]
