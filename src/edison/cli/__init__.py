"""
Edison CLI package.

Provides the command-line interface with auto-discovery of commands
from subfolders (session/, task/, config/, etc.).

Framework utilities for building CLI commands:
- _output: Output formatting (JSON/text modes)
- _args: Common argument registration helpers
- _utils: Shared CLI utilities
"""
from ._output import OutputFormatter, format_json, print_success, print_error
from ._args import (
    add_json_flag,
    add_repo_root_flag,
    add_session_id_arg,
    add_record_id_arg,
    add_force_flag,
    add_dry_run_flag,
    add_verbose_flag,
    add_record_type_arg,
    add_standard_flags,
)
from ._utils import (
    get_repo_root,
    validate_and_get_session_id,
    detect_record_type,
    get_record_type,
    get_repository,
    normalize_record_id,
    run_cli_command,
)

__all__ = [
    # Output formatting
    "OutputFormatter",
    "format_json",
    "print_success",
    "print_error",
    # Argument helpers
    "add_json_flag",
    "add_repo_root_flag",
    "add_session_id_arg",
    "add_record_id_arg",
    "add_force_flag",
    "add_dry_run_flag",
    "add_verbose_flag",
    "add_record_type_arg",
    "add_standard_flags",
    # Utilities
    "get_repo_root",
    "validate_and_get_session_id",
    "detect_record_type",
    "get_record_type",
    "get_repository",
    "normalize_record_id",
    "run_cli_command",
]
