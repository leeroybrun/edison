"""Utility helpers for Edison core."""

from types import ModuleType

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
from .git import (
    get_repo_root,
    get_current_branch,
    is_clean_working_tree,
    is_worktree,
    get_worktree_parent,
)
from .time import utc_now, utc_timestamp, parse_iso8601
from .json_io import read_json, write_json_atomic, update_json
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
from .mcp import TOOL_NAME as MCP_TOOL_NAME, resolve_working_directory, format_clink_cli_command
from .text import (
    dry_duplicate_report,
    render_conditional_includes,
    ENGINE_VERSION,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)

# Create a 'cli' compatibility module for code that imports `from edison.core.utils import cli`
# This allows code to use `cli.output_json()`, `cli.parse_common_args()`, etc.
cli = ModuleType("edison.core.utils.cli")
cli.parse_common_args = parse_common_args
cli.session_parent = session_parent
cli.dry_run_parent = dry_run_parent
cli.output_json = output_json
cli.output_table = output_table
cli.confirm = confirm
cli.error = error
cli.success = success

__all__ = [
    "cli",  # Compatibility module for code using `from edison.core.utils import cli`
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
