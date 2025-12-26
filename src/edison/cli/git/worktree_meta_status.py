"""
Edison git worktree-meta-status command.

SUMMARY: Show shared-state meta worktree status
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag
from edison.core.session import worktree

SUMMARY = "Show shared-state meta worktree status"


def register_args(parser: argparse.ArgumentParser) -> None:
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        status = worktree.get_meta_worktree_status()
        if formatter.json_mode:
            formatter.json_output(status)
        else:
            formatter.text("Meta worktree status:")
            formatter.text(f"  Mode: {status.get('mode')}")
            formatter.text(f"  Primary: {status.get('primary_repo_dir')}")
            formatter.text(f"  Path: {status.get('meta_path')}")
            formatter.text(f"  Branch: {status.get('meta_branch')}")
            formatter.text(f"  Exists: {status.get('exists')}")
            formatter.text(f"  Registered: {status.get('registered')}")
        return 0
    except Exception as e:
        formatter.error(e, error_code="worktree_meta_status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))

