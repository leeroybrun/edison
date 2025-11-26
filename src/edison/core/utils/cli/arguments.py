"""CLI argument parsing helpers.

This module provides argparse parent parsers and common argument helpers
for building consistent Edison CLI commands.

Extracted from the original cli.py god file to follow Single Responsibility Principle.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def parse_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Attach common Edison CLI flags to ``parser``.

    Flags:
        --json      Output machine-readable JSON
        -y/--yes    Assume yes for confirmations
        --repo-root Override repository root detection

    Args:
        parser: The ArgumentParser to attach flags to

    Returns:
        The same parser instance for method chaining
    """
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "-y", "--yes", dest="yes", action="store_true", help="Assume yes for prompts"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root override (bypasses auto-detection)",
    )
    return parser


def session_parent(
    help_text: str | None = None, *, required: bool = False
) -> argparse.ArgumentParser:
    """Return an argparse parent that adds the ``--session`` flag.

    Args:
        help_text: Override the default help copy.
        required: When ``True``, mark the flag as required for commands that
            must operate within an explicit session.

    Returns:
        A parent ArgumentParser with add_help=False
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--session",
        required=required,
        help=help_text
        or "Session ID to scope the command (e.g., sess-001). "
        "Auto-detects from the current worktree when omitted.",
    )
    return parser


def dry_run_parent(help_text: str | None = None) -> argparse.ArgumentParser:
    """Return an argparse parent that adds a standard ``--dry-run`` toggle.

    Args:
        help_text: Override the default help copy.

    Returns:
        A parent ArgumentParser with add_help=False
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=help_text or "Preview actions without making changes.",
    )
    return parser


__all__ = [
    "parse_common_args",
    "session_parent",
    "dry_run_parent",
]
