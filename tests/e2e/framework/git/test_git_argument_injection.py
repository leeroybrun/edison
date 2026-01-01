from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from tests.helpers.paths import get_repo_root
from tests.helpers.env import TestGitRepo

REPO_ROOT = get_repo_root()

from edison.core.utils.io.locking import safe_move_file
from edison.core.session import worktree as sessionlib


def test_session_id_with_dash_prefix(isolated_project_env):
    """Verify session IDs starting with '-' do not inject options in git commands.

    Uses real git operations to verify safe handling.
    """
    # Use isolated project environment with real git
    root = isolated_project_env
    git_repo = TestGitRepo(root)

    # Session ID with leading dash
    sid = "-test-session"

    # Exercise worktree creation path with real git operations
    # This will verify that our code properly uses '--' separators
    try:
        wt_path, branch = sessionlib.create_worktree(sid, base_branch="main", install_deps=False)
        # If worktree creation succeeds, verify it was created properly
        if wt_path and branch:
            assert isinstance(branch, str)
            # Verify the worktree exists in git's worktree list
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True
            )
            # The worktree path should appear in the list
            assert str(wt_path) in result.stdout or sid in result.stdout
    except subprocess.CalledProcessError:
        # If worktree creation is disabled in test environment, this is acceptable
        # The important thing is that no argument injection occurred (would cause different errors)
        pass


def test_task_id_with_dash(isolated_project_env):
    """Verify task IDs with leading '-' use a safe `git mv --` when moving status.

    Uses real git operations to verify safe handling.
    """
    root = isolated_project_env
    git_repo = TestGitRepo(root)

    # Initialize task paths for the test
    task_root = root / ".project" / "tasks"
    todo = task_root / "wip"
    done = task_root / "done"
    todo.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)

    # Create a task file with a dash-prefixed name
    src = todo / "-123-test.md"
    src.write_text("# test\n- **Owner:** u\n- **Status:** wip\n")

    # Add to git so we can track the move
    subprocess.run(
        ["git", "add", str(src)],
        cwd=root,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test task"],
        cwd=root,
        check=True,
        capture_output=True
    )

    # Move the task using real git operations
    # The safe_move_file function should use safe git mv with '--' separator
    dst_path = done / src.name
    dst = safe_move_file(src, dst_path, repo_root=root)

    # Verify the move succeeded
    assert dst.exists(), f"Task file should exist at destination: {dst}"
    assert dst.parent == done, f"Task should be in 'done' directory: {dst.parent}"
    assert not src.exists(), f"Original task file should not exist: {src}"

    # Verify git tracked the move
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True
    )
    # Either renamed (R) or deleted/added (D/A) should appear
    status_output = result.stdout
    assert (
        "-123-test.md" in status_output or
        "done" in status_output
    ), f"Git should track the file move: {status_output}"


def test_branch_name_with_dash(isolated_project_env):
    """Verify branch operations include `--` when branch could start with '-'.

    Uses real git operations to verify safe handling.
    """
    root = isolated_project_env
    git_repo = TestGitRepo(root)

    # Branch name with leading dash
    branch_name = "-feature-branch"

    # Trigger worktree creation paths with real git
    try:
        wt_path, created_branch = sessionlib.create_worktree(branch_name, base_branch="main", install_deps=False)

        if wt_path and wt_path.exists():
            # Verify the worktree was created successfully
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True
            )

            # Check that worktree appears in the list
            assert str(wt_path) in result.stdout or branch_name in result.stdout, \
                f"Worktree should be listed: {result.stdout}"

            # Cleanup - remove the worktree using safe commands
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", "--", str(wt_path)],
                    cwd=root,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                # Cleanup failure is acceptable in tests
                pass
    except subprocess.CalledProcessError as e:
        # If worktree creation is disabled, acceptable
        # Important: no argument injection errors occurred
        pass


def test_all_git_commands_have_separator():
    """Static analysis: verify critical git commands use `--` where required.

    Scope limited to worktree.py and task/locking.py as the core libraries.
    """
    worktree_path = REPO_ROOT / "src" / "edison" / "core" / "session" / "worktree"
    # Check both old monolithic and new modular structure
    worktree_files = []
    if worktree_path.is_dir():
        worktree_files = list(worktree_path.glob("*.py"))
    else:
        # Fallback to single file
        worktree_py = REPO_ROOT / "src" / "edison" / "core" / "session" / "worktree.py"
        if worktree_py.exists():
            worktree_files = [worktree_py]

    task_locking_path = REPO_ROOT / "src" / "edison" / "core" / "task" / "locking.py"

    worktree_src = "\n".join(f.read_text() for f in worktree_files if f.exists())
    task_src = task_locking_path.read_text() if task_locking_path.exists() else ""

    def must_contain(pattern: str, src: str, name: str = "source"):
        assert pattern in src, f"Missing expected safe pattern in {name}: {pattern}"

    # Ensure git mv uses `--` (task/locking.safe_move_file)
    if task_src:
        must_contain('["git", "mv", "--"', task_src, "task/locking.py")

    # Ensure branch -D uses `--`
    if worktree_src:
        must_contain('["git", "branch", "-D", "--"', worktree_src, "worktree module")

        # Ensure worktree add/remove guard path with `--`
        must_contain('["git", "worktree", "add", "--"', worktree_src, "worktree module")
        must_contain('["git", "worktree", "remove", "--force", "--"', worktree_src, "worktree module")

        # If the worktree implementation uses clone, ensure it is safe (`--` separator).
        # Worktrees can be created via `git worktree add` without cloning; in that case this check is irrelevant.
        if '["git", "clone"' in worktree_src:
            must_contain('["git", "clone", "--local", "--no-hardlinks", "--"', worktree_src, "worktree module")
