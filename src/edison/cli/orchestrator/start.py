"""
Edison orchestrator start command.

SUMMARY: Start an orchestrator session with optional worktree
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import (
    OutputFormatter,
    add_dry_run_flag,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
)

SUMMARY = "Start an orchestrator session with optional worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        help="Orchestrator profile name (default: from config)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Initial prompt text to send to orchestrator",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        help="Path to file containing initial prompt",
    )
    parser.add_argument(
        "--no-worktree",
        action="store_true",
        help="Skip worktree creation",
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Detach orchestrator process (run in background)",
    )
    add_json_flag(parser)
    add_dry_run_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Start an orchestrator session."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        from edison.core.session.lifecycle.autostart import SessionAutoStart

        repo_root = get_repo_root(args)

        # Build prompt path if provided
        prompt_path = None
        if args.prompt_file:
            prompt_path = Path(args.prompt_file)
            if not prompt_path.is_absolute():
                prompt_path = repo_root / prompt_path

        autostart = SessionAutoStart(project_root=repo_root)

        result = autostart.start(
            orchestrator_profile=args.profile,
            initial_prompt_path=prompt_path,
            no_worktree=args.no_worktree,
            detach=args.detach,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            formatter.json_output(result)
            return 0

        if result.get("status") == "success":
            session_id = result.get("session_id")
            worktree_path = result.get("worktree_path")
            pid = result.get("orchestrator_pid")

            formatter.text(f"Started session: {session_id}")
            if worktree_path:
                formatter.text(f"  Worktree: {worktree_path}")
            if pid:
                formatter.text(f"  Orchestrator PID: {pid}")
            return 0
        else:
            formatter.error(f"Failed to start: {result.get('error', 'Unknown error')}", error_code="start_error")
            return 1

    except Exception as e:
        formatter.error(e, error_code="orchestrator_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
