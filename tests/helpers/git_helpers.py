"""Git operation helpers for E2E tests."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional
from edison.core.utils.subprocess import run_with_timeout


def git_init(repo_path: Path, branch: str = "main") -> None:
    """Initialize a git repository.

    Args:
        repo_path: Path to repository
        branch: Initial branch name
    """
    run_with_timeout(
        ["git", "init", "-b", branch],
        cwd=repo_path,
        check=True,
        capture_output=True
    )


def git_commit(repo_path: Path, message: str, allow_empty: bool = False) -> None:
    """Create a git commit.

    Args:
        repo_path: Path to repository/worktree
        message: Commit message
        allow_empty: Allow empty commits
    """
    cmd = ["git", "add", "-A"]
    run_with_timeout(cmd, cwd=repo_path, check=True, capture_output=True)

    cmd = ["git", "commit", "-m", message]
    if allow_empty:
        cmd.append("--allow-empty")

    run_with_timeout(cmd, cwd=repo_path, check=True, capture_output=True)


def git_create_worktree(
    repo_path: Path,
    worktree_path: Path,
    branch: str,
    base_branch: str = "main"
) -> None:
    """Create a git worktree.

    Args:
        repo_path: Path to main repository
        worktree_path: Path for new worktree
        branch: New branch name
        base_branch: Branch to base new branch on
    """
    run_with_timeout(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch],
        cwd=repo_path,
        check=True,
        capture_output=True
    )


def git_remove_worktree(repo_path: Path, worktree_path: Path, force: bool = False) -> None:
    """Remove a git worktree.

    Args:
        repo_path: Path to main repository
        worktree_path: Path to worktree to remove
        force: Force removal even if worktree has changes
    """
    cmd = ["git", "worktree", "remove", str(worktree_path)]
    if force:
        cmd.append("--force")

    run_with_timeout(cmd, cwd=repo_path, check=True, capture_output=True)


def git_list_worktrees(repo_path: Path) -> List[str]:
    """List all worktrees in repository.

    Args:
        repo_path: Path to main repository

    Returns:
        List of worktree paths
    """
    result = run_with_timeout(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )

    worktrees = []
    for line in result.stdout.split("\n"):
        if line.startswith("worktree "):
            worktrees.append(line.split(" ", 1)[1])

    return worktrees


def git_diff_files(
    repo_path: Path,
    base: str = "main",
    target: Optional[str] = None
) -> List[str]:
    """Get list of changed files between commits.

    Args:
        repo_path: Path to repository/worktree
        base: Base ref (e.g., "main")
        target: Target ref (defaults to HEAD)

    Returns:
        List of changed file paths
    """
    cmd = ["git", "diff", "--name-only", base]
    if target:
        cmd.append(target)

    result = run_with_timeout(
        cmd,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )

    return [f.strip() for f in result.stdout.split("\n") if f.strip()]


def git_current_branch(repo_path: Path) -> str:
    """Get current branch name.

    Args:
        repo_path: Path to repository/worktree

    Returns:
        Current branch name
    """
    result = run_with_timeout(
        ["git", "branch", "--show-current"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def git_branch_exists(repo_path: Path, branch: str) -> bool:
    """Check if a branch exists.

    Args:
        repo_path: Path to repository
        branch: Branch name to check

    Returns:
        True if branch exists
    """
    result = run_with_timeout(
        ["git", "branch", "--list", branch],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    return branch in result.stdout


def git_merge(
    repo_path: Path,
    branch: str,
    into: str = "main",
    no_ff: bool = True
) -> subprocess.CompletedProcess:
    """Merge a branch.

    Args:
        repo_path: Path to repository
        branch: Branch to merge
        into: Target branch (default: main)
        no_ff: Create merge commit even if fast-forward possible

    Returns:
        CompletedProcess result
    """
    # Checkout target branch
    run_with_timeout(
        ["git", "checkout", into],
        cwd=repo_path,
        check=True,
        capture_output=True
    )

    # Merge
    cmd = ["git", "merge", branch]
    if no_ff:
        cmd.append("--no-ff")

    return run_with_timeout(
        cmd,
        cwd=repo_path,
        capture_output=True,
        text=True
    )


def git_status(repo_path: Path, short: bool = True) -> str:
    """Get git status output.

    Args:
        repo_path: Path to repository/worktree
        short: Use short format

    Returns:
        Git status output
    """
    cmd = ["git", "status"]
    if short:
        cmd.append("--short")

    result = run_with_timeout(
        cmd,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout


def git_log(
    repo_path: Path,
    max_count: int = 10,
    oneline: bool = True
) -> List[str]:
    """Get git commit log.

    Args:
        repo_path: Path to repository/worktree
        max_count: Maximum number of commits
        oneline: Use oneline format

    Returns:
        List of commit messages/hashes
    """
    cmd = ["git", "log", f"-{max_count}"]
    if oneline:
        cmd.append("--oneline")

    result = run_with_timeout(
        cmd,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True
    )

    return [line.strip() for line in result.stdout.split("\n") if line.strip()]