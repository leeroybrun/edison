"""
Edison orchestrator start command.

SUMMARY: Start an orchestrator session with optional worktree
"""

from __future__ import annotations

import argparse
import tempfile
import sys
from pathlib import Path

from edison.core.session.lifecycle.autostart import SessionAutoStart
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
        "--start-prompt",
        type=str,
        help="Start prompt ID to load from templates and send to orchestrator (e.g. AUTO_NEXT). See `edison list --type start --format detail`.",
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
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Create session/worktree but do not launch the orchestrator process",
    )
    add_json_flag(parser)
    add_dry_run_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Start an orchestrator session."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        if formatter.json_mode and not args.dry_run and not args.detach and not bool(getattr(args, "no_launch", False)):
            formatter.error(
                ValueError("--json requires --detach or --no-launch (interactive mode emits non-JSON output)"),
                error_code="args_error",
            )
            return 2


        repo_root = get_repo_root(args)

        # Build prompt path if provided (file or inline text). Autostart reads from a file.
        prompt_path: Path | None = None
        if args.prompt_file:
            prompt_path = Path(args.prompt_file)
            if not prompt_path.is_absolute():
                prompt_path = repo_root / prompt_path
        elif getattr(args, "start_prompt", None):
            from edison.core.session.start_prompts import read_start_prompt

            content = read_start_prompt(repo_root, str(args.start_prompt))
            tmp = tempfile.NamedTemporaryFile(prefix="edison-start-prompt-", suffix=".md", delete=False)
            tmp.write(content.encode("utf-8"))
            tmp.flush()
            tmp.close()
            prompt_path = Path(tmp.name)
        elif getattr(args, "prompt", None):
            text = str(args.prompt)
            tmp = tempfile.NamedTemporaryFile(prefix="edison-prompt-", suffix=".md", delete=False)
            tmp.write(text.encode("utf-8"))
            tmp.flush()
            tmp.close()
            prompt_path = Path(tmp.name)

        autostart = SessionAutoStart(project_root=repo_root)

        result = autostart.start(
            orchestrator_profile=args.profile,
            initial_prompt_path=prompt_path,
            no_worktree=args.no_worktree,
            detach=args.detach,
            dry_run=args.dry_run,
            launch_orchestrator=not bool(getattr(args, "no_launch", False)),
        )

        if args.dry_run:
            formatter.json_output(result)
            return 0

        if result.get("status") == "success":
            session_id = result.get("session_id")
            worktree_path = result.get("worktree_path")
            pid = result.get("orchestrator_pid")
            process = result.get("orchestrator_process")
            launched = process is not None and not bool(getattr(args, "no_launch", False))

            if formatter.json_mode:
                # Never emit unserializable objects in JSON mode.
                formatter.json_output(
                    {
                        "status": "success",
                        "session_id": session_id,
                        "worktree_path": worktree_path,
                        "orchestrator_pid": pid,
                        "launched": launched,
                        "detached": bool(args.detach),
                    }
                )
                return 0

            # In interactive mode (not detached), wait for the process
            if not args.detach and process is not None:
                formatter.text(f"Started session: {session_id}")
                if worktree_path:
                    formatter.text(f"  Worktree: {worktree_path}")
                    formatter.text(f"  (Launched orchestrator with cwd={worktree_path})")
                formatter.text("")  # Blank line before interactive session
                try:
                    # Wait for the orchestrator process to complete
                    return_code = process.wait()
                    return return_code
                except KeyboardInterrupt:
                    # User cancelled - gracefully terminate
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()
                    return 130  # Standard exit code for Ctrl+C
            else:
                # Detached mode - just report and exit
                formatter.text(f"Started session: {session_id}")
                if worktree_path:
                    formatter.text(f"  Worktree: {worktree_path}")
                    formatter.text(f"  Tip: cd {worktree_path} (never work in the primary checkout)")
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
