"""
Edison CLI package.

Provides the command-line interface with auto-discovery of commands
from subfolders (session/, task/, config/, etc.).

Framework utilities for building CLI commands:
- _output: Output formatting (JSON/text modes)
- _args: Common argument registration helpers
- _utils: Shared CLI utilities
"""
from ._output import OutputFormatter
from ._args import (
    add_json_flag,
    add_repo_root_flag,
    add_force_flag,
    add_dry_run_flag,
)
from ._utils import (
    get_repo_root,
    detect_record_type,
    get_repository,
    resolve_existing_task_id,
    format_display_path,
    resolve_session_id,
)

__all__ = [
    # Output formatting
    "OutputFormatter",
    # Argument helpers
    "add_json_flag",
    "add_repo_root_flag",
    "add_force_flag",
    "add_dry_run_flag",
    # Utilities
    "get_repo_root",
    "detect_record_type",
    "get_repository",
    "resolve_existing_task_id",
    "format_display_path",
    "resolve_session_id",
]
