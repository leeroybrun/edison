"""CLI utilities for Edison.

This package provides CLI helpers:
- Arguments: argparse helpers and parent parsers
- Errors: structured error handling and JSON output
- Output: formatting for JSON, tables, prompts
"""
from __future__ import annotations

from .arguments import (
    dry_run_parent,
    parse_common_args,
    session_parent,
)
from .errors import (
    cli_error,
    json_output,
    run_cli,
)
from .output import (
    confirm,
    error,
    output_json,
    output_table,
    success,
)

__all__ = [
    # arguments
    "parse_common_args",
    "session_parent",
    "dry_run_parent",
    # errors
    "json_output",
    "cli_error",
    "run_cli",
    # output
    "output_json",
    "output_table",
    "confirm",
    "error",
    "success",
]



