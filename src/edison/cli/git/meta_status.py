"""
Edison git meta-status command.

SUMMARY: Show shared-state meta worktree status with git status details
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.cli import OutputFormatter, add_json_flag
from edison.core.session import worktree

SUMMARY = "Show shared-state meta worktree status with git status details"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    add_json_flag(parser)


def _get_git_status(cwd: Path) -> Dict[str, Any]:
    """Get git status information for a directory.

    Args:
        cwd: Directory to check git status in

    Returns:
        Dict with dirty status and list of changed files
    """
    result: Dict[str, Any] = {"dirty": False, "changed_files": []}

    if not cwd.exists():
        return result

    try:
        # Get status porcelain output
        cp = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        status_output = cp.stdout.strip()
        if status_output:
            result["dirty"] = True
            changed_files: List[str] = []
            for line in status_output.split("\n"):
                if line:
                    # Status is first two characters, then space, then path
                    file_path = line[3:] if len(line) > 3 else line
                    changed_files.append(file_path.strip())
            result["changed_files"] = changed_files
    except subprocess.CalledProcessError:
        pass
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    return result


def main(args: argparse.Namespace) -> int:
    """Execute the meta-status command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Get base meta worktree status
        status = worktree.get_meta_worktree_status()

        # Add git status information if meta worktree exists
        meta_path_str = status.get("meta_path", "")
        meta_path = Path(meta_path_str) if meta_path_str else None

        if meta_path and meta_path.exists():
            git_status = _get_git_status(meta_path)
            status["dirty"] = git_status["dirty"]
            status["changed_files"] = git_status["changed_files"]

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

            if not status.get("exists"):
                formatter.text("")
                formatter.text("Hint: Run 'edison git worktree-meta-init' to initialize the meta worktree.")
            else:
                if status.get("dirty"):
                    formatter.text(f"  Dirty: {status.get('dirty')}")
                    changed = status.get("changed_files", [])
                    if changed:
                        formatter.text("  Changed files:")
                        for f in changed:
                            formatter.text(f"    - {f}")

        return 0
    except Exception as e:
        formatter.error(e, error_code="meta_status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
