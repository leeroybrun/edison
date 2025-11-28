"""Common CLI argument registration utilities.

This module provides reusable argument registration functions to reduce
duplication across CLI commands.
"""
from __future__ import annotations

import argparse


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    """Add --json flag for JSON output mode.

    Args:
        parser: ArgumentParser to add the flag to
    """
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )


def add_repo_root_flag(parser: argparse.ArgumentParser) -> None:
    """Add --repo-root flag for repository root override.

    Args:
        parser: ArgumentParser to add the flag to
    """
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def add_session_id_arg(
    parser: argparse.ArgumentParser,
    required: bool = True,
) -> None:
    """Add session-id argument.

    Args:
        parser: ArgumentParser to add the argument to
        required: Whether the argument is required
    """
    parser.add_argument(
        "--session-id",
        "--id",
        dest="session_id",
        required=required,
        help="Session identifier (e.g., sess-001)",
    )


def add_record_id_arg(
    parser: argparse.ArgumentParser,
    name: str = "record_id",
    help_text: str = "Record identifier (task or QA)",
    required: bool = True,
) -> None:
    """Add record ID positional argument.

    Args:
        parser: ArgumentParser to add the argument to
        name: Argument name (default: record_id)
        help_text: Help text for the argument
        required: Whether the argument is required
    """
    if required:
        parser.add_argument(name, help=help_text)
    else:
        parser.add_argument(name, nargs="?", help=help_text)


def add_force_flag(parser: argparse.ArgumentParser) -> None:
    """Add --force flag.

    Args:
        parser: ArgumentParser to add the flag to
    """
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force operation without confirmation",
    )


def add_dry_run_flag(parser: argparse.ArgumentParser) -> None:
    """Add --dry-run flag.

    Args:
        parser: ArgumentParser to add the flag to
    """
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without making changes",
    )


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    """Add --verbose flag.

    Args:
        parser: ArgumentParser to add the flag to
    """
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )


def add_record_type_arg(
    parser: argparse.ArgumentParser,
    required: bool = False,
) -> None:
    """Add --type argument for record type selection.

    Args:
        parser: ArgumentParser to add the argument to
        required: Whether the argument is required
    """
    parser.add_argument(
        "--type",
        "-t",
        dest="record_type",
        choices=["task", "qa"],
        required=required,
        help="Record type (task or qa). Auto-detected if not specified.",
    )


def add_standard_flags(parser: argparse.ArgumentParser) -> None:
    """Add standard flags that most commands use.

    Adds: --json, --repo-root

    Args:
        parser: ArgumentParser to add flags to
    """
    add_json_flag(parser)
    add_repo_root_flag(parser)


__all__ = [
    "add_json_flag",
    "add_repo_root_flag",
    "add_session_id_arg",
    "add_record_id_arg",
    "add_force_flag",
    "add_dry_run_flag",
    "add_verbose_flag",
    "add_record_type_arg",
    "add_standard_flags",
]
