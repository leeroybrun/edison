"""Worktree post-install command helpers."""

from __future__ import annotations

from pathlib import Path

from edison.core.utils.subprocess import run_with_timeout

__all__ = ["_run_post_install_commands"]


def _run_post_install_commands(*, worktree_path: Path, commands: list[str], timeout: int) -> None:
    """Run project-configured post-install commands inside the worktree."""
    for cmd in commands:
        result = run_with_timeout(
            ["bash", "-lc", cmd],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0:
            tail_out = "\n".join((result.stdout or "").splitlines()[-25:])
            tail_err = "\n".join((result.stderr or "").splitlines()[-25:])
            raise RuntimeError(
                "Post-install command failed in worktree:\n"
                f"  cwd: {worktree_path}\n"
                f"  cmd: {cmd}\n"
                f"  exit: {result.returncode}\n"
                f"  stdout (tail):\n{tail_out}\n"
                f"  stderr (tail):\n{tail_err}"
            )
