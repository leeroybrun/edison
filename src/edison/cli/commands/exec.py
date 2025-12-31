"""
Edison exec command.

SUMMARY: Run a command via Edison (optional shims + audit logging)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_repo_root_flag, get_repo_root
from edison.cli._exec import run_exec

SUMMARY = "Run a command via Edison (optional shims + audit logging)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "argv",
        nargs=argparse.REMAINDER,
        help="Command to run (use `--` before the command).",
    )
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=False)
    repo_root = get_repo_root(args)

    argv = list(getattr(args, "argv", []) or [])
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        formatter.error("Usage: edison exec -- <command> [args...]", error_code="missing_command")
        return 2

    return run_exec(repo_root=repo_root, argv=argv, context="shell")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

