"""
Edison git worktree-meta-init command.

SUMMARY: Initialize shared-state meta worktree
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_dry_run_flag
from edison.core.session import worktree

SUMMARY = "Initialize shared-state meta worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Do not create; only show computed meta worktree status",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the meta worktree + orphan meta branch (destructive)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force removal of existing meta worktree (use with --recreate)",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        if args.no_create:
            status = worktree.get_meta_worktree_status()
        elif getattr(args, "recreate", False):
            status = worktree.recreate_meta_shared_state(
                dry_run=bool(getattr(args, "dry_run", False)),
                force=bool(getattr(args, "force", False)),
            )
        else:
            status = worktree.initialize_meta_shared_state(dry_run=bool(getattr(args, "dry_run", False)))

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
            if "created" in status:
                formatter.text(f"  Created: {status.get('created')}")
            if "primary_links_updated" in status:
                formatter.text(f"  Primary links updated: {status.get('primary_links_updated')}")
            if "session_worktrees_updated" in status:
                formatter.text(f"  Session worktrees updated: {status.get('session_worktrees_updated')}")
        return 0
    except Exception as e:
        formatter.error(e, error_code="worktree_meta_init_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
