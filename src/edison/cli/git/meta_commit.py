"""
Edison git meta-commit command.

SUMMARY: Commit changes in the shared-state meta worktree
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from edison.cli import OutputFormatter, add_json_flag
from edison.core.session import worktree

SUMMARY = "Commit changes in the shared-state meta worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        default=None,
        help="Commit message (required)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        default=False,
        help="Stage all modified and deleted files before committing",
    )
    add_json_flag(parser)


def _run_git_commit(
    cwd: Path,
    message: str,
    stage_all: bool = False,
) -> Dict[str, Any]:
    """Run git commit in the specified directory.

    Args:
        cwd: Directory to run git commit in
        message: Commit message
        stage_all: If True, run with -a flag

    Returns:
        Dict with commit result (sha, committed, error)
    """
    result: Dict[str, Any] = {
        "committed": False,
        "commit_sha": None,
        "error": None,
    }

    try:
        # Build commit command
        cmd = ["git", "commit", "-m", message]
        if stage_all:
            cmd.insert(2, "-a")

        cp = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        # Get the commit SHA
        sha_cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        sha = sha_cp.stdout.strip()

        result["committed"] = True
        result["commit_sha"] = sha
        result["status"] = "success"

    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        error_msg = stderr or stdout or "Git commit failed"
        result["error"] = error_msg
        # Check if it's just "nothing to commit"
        if "nothing to commit" in error_msg.lower():
            result["committed"] = False
            result["status"] = "nothing_to_commit"
        else:
            result["status"] = "error"
    except subprocess.TimeoutExpired:
        result["error"] = "Git commit timed out"
        result["status"] = "timeout"
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "error"

    return result


def main(args: argparse.Namespace) -> int:
    """Execute the meta-commit command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    # Validate required message argument
    message = getattr(args, "message", None)
    if not message:
        if formatter.json_mode:
            formatter.json_output({
                "error": "missing_message",
                "message": "Commit message is required. Use -m or --message.",
            })
        else:
            print("Error: Commit message is required. Use -m or --message.", file=sys.stderr)
        return 1

    try:
        # Get meta worktree status
        status = worktree.get_meta_worktree_status()

        meta_path_str = status.get("meta_path", "")
        meta_path = Path(meta_path_str) if meta_path_str else None
        exists = status.get("exists", False)

        # Check if meta worktree exists
        if not meta_path or not exists:
            if formatter.json_mode:
                formatter.json_output({
                    "error": "meta_worktree_missing",
                    "message": "Meta worktree does not exist. Run 'edison git worktree-meta-init' to initialize.",
                })
            else:
                print(
                    "Error: Meta worktree is missing. "
                    "Run 'edison git worktree-meta-init' to initialize.",
                    file=sys.stderr,
                )
            return 1

        # Run git commit in the meta worktree
        stage_all = getattr(args, "all", False)
        result = _run_git_commit(meta_path, message, stage_all=stage_all)

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if result.get("committed"):
                sha = result.get("commit_sha", "")
                short_sha = sha[:8] if sha else ""
                formatter.text(f"Committed to meta worktree: {short_sha}")
                formatter.text(f"  Message: {message}")
            elif result.get("status") == "nothing_to_commit":
                formatter.text("Nothing to commit in meta worktree.")
            else:
                error = result.get("error", "Unknown error")
                print(f"Error: {error}", file=sys.stderr)
                return 1

        return 0 if result.get("committed") or result.get("status") == "nothing_to_commit" else 1

    except Exception as e:
        formatter.error(e, error_code="meta_commit_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
