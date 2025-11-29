"""Utility helpers for Edison core.

This package provides consolidated utilities:
- io/: File I/O operations (atomic writes, JSON, YAML, locking)
- git/: Git repository operations
- paths/: Path resolution
- process/: Process inspection
- cli/: CLI helpers
- time: Time utilities
- subprocess: Subprocess management
- text: Text processing
- mcp: MCP/clink helpers
- dependencies: External tool detection
- resilience: Retry and recovery patterns
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

# CLI utilities
from .cli import (
    cli_error,
    confirm,
    dry_run_parent,
    error,
    json_output,
    output_json,
    output_table,
    parse_common_args,
    run_cli,
    session_parent,
    success,
)

# Git utilities - lazy imports to avoid circular dependency with paths
from .git import (
    get_changed_files,
    get_current_branch,
    get_git_root,
    get_repo_root,
    get_worktree_info,
    get_worktree_parent,
    is_clean_working_tree,
    is_git_repository,
    is_worktree,
)

# I/O utilities
from .io import (
    HAS_YAML,
    LockTimeoutError,
    PathLike,
    acquire_file_lock,
    atomic_write,
    dump_yaml_string,
    ensure_directory,
    ensure_parent_dir,
    get_file_locking_config,
    parse_yaml_string,
    read_json,
    read_text,
    read_yaml,
    update_json,
    write_json_atomic,
    write_text,
    write_yaml,
)
from .merge import deep_merge, merge_arrays

# Paths utilities
from .paths import (
    DEFAULT_PROJECT_CONFIG_PRIMARY,
    EdisonPathError,
    PathResolver,
    ProjectManagementPaths,
    _PROJECT_ROOT_CACHE,
    find_evidence_round,
    get_management_paths,
    get_project_config_dir,
    get_project_path,
    list_evidence_rounds,
    resolve_project_root,
)

# Process utilities
from .process import (
    HAS_PSUTIL,
    find_topmost_process,
    infer_session_id,
    is_process_alive,
)

# Subprocess utilities - lazy import to avoid circular dependency
# Import directly from edison.core.utils.subprocess when needed

# Text utilities - lazy import ENGINE_VERSION to avoid circular import
from .text import (
    _shingles,
    _strip_headings_and_code,
    _tokenize,
    dry_duplicate_report,
    render_conditional_includes,
    get_engine_version,
)

# Time utilities
from .time import parse_iso8601, utc_now, utc_timestamp

# Lazily import MCP helpers to avoid circular imports through SessionContext
# and PathResolver during package import.

def get_mcp_tool_name() -> str:
    """Get the MCP tool name from configuration.

    Returns:
        str: The configured MCP tool name

    Raises:
        RuntimeError: If config cannot be loaded or tool name is missing
    """
    from . import mcp as _mcp

    return _mcp.get_tool_name()


def resolve_working_directory(
    session_id: Optional[str] = None, *, start_path: Optional[Path | str] = None
):
    from . import mcp as _mcp

    return _mcp.resolve_working_directory(session_id=session_id, start_path=start_path)


def format_clink_cli_command(
    *,
    cli_name: str,
    role: Optional[str] = None,
    prompt: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    extra_args: Optional[dict] = None,
) -> str:
    from . import mcp as _mcp

    # Default to configured tool name if not provided
    if tool_name is None:
        tool_name = get_mcp_tool_name()

    return _mcp.format_clink_cli_command(
        cli_name=cli_name,
        role=role,
        prompt=prompt,
        session_id=session_id,
        tool_name=tool_name,
        extra_args=extra_args,
    )


# NOTE: dependencies module is NOT imported here to avoid import-time coupling
# Import directly: from edison.core.utils.dependencies import detect_uvx, detect_zen_mcp_server

__all__ = [
    # CLI
    "parse_common_args",
    "session_parent",
    "dry_run_parent",
    "json_output",
    "cli_error",
    "run_cli",
    "output_json",
    "output_table",
    "confirm",
    "error",
    "success",
    # Git
    "is_git_repository",
    "get_git_root",
    "get_repo_root",
    "get_current_branch",
    "is_clean_working_tree",
    "is_worktree",
    "get_worktree_parent",
    "get_worktree_info",
    "get_changed_files",
    # I/O
    "PathLike",
    "ensure_parent_dir",
    "ensure_directory",
    "atomic_write",
    "read_text",
    "write_text",
    "read_json",
    "write_json_atomic",
    "update_json",
    "HAS_YAML",
    "read_yaml",
    "write_yaml",
    "parse_yaml_string",
    "dump_yaml_string",
    "acquire_file_lock",
    "LockTimeoutError",
    "get_file_locking_config",
    # Paths
    "EdisonPathError",
    "PathResolver",
    "resolve_project_root",
    "get_project_path",
    "_PROJECT_ROOT_CACHE",
    "ProjectManagementPaths",
    "get_management_paths",
    "DEFAULT_PROJECT_CONFIG_PRIMARY",
    "get_project_config_dir",
    "find_evidence_round",
    "list_evidence_rounds",
    # Process
    "HAS_PSUTIL",
    "is_process_alive",
    "find_topmost_process",
    "infer_session_id",
    # MCP
    "MCP_TOOL_NAME",
    "get_mcp_tool_name",
    "resolve_working_directory",
    "format_clink_cli_command",
    # Time
    "utc_now",
    "utc_timestamp",
    "parse_iso8601",
    # Subprocess - import from edison.core.utils.subprocess directly
    # Text
    "dry_duplicate_report",
    "render_conditional_includes",
    "get_engine_version",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    # Merge
    "deep_merge",
    "merge_arrays",
    # Config - import from edison.core.utils.config directly when needed
    # Functions available: load_config_section, get_states_for_domain,
    # get_initial_state, get_active_state, get_completed_state,
    # get_final_state, get_semantic_state
]
