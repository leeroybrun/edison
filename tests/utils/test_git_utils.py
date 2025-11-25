from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest


@pytest.fixture()
def git_module(isolated_project_env: Path, monkeypatch):
    # Commit initial content so worktree operations are allowed.
    subprocess.run(["git", "add", "-A"], cwd=isolated_project_env, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=isolated_project_env, check=True)
    import edison.core.utils.git as git  # type: ignore

    importlib.reload(git)
    return git


def test_get_repo_root_detects_git_top(git_module, isolated_project_env: Path, tmp_path: Path):
    nested = isolated_project_env / "nested" / "child"
    nested.mkdir(parents=True, exist_ok=True)
    root = git_module.get_repo_root(start_path=nested)
    assert root == isolated_project_env


def test_current_branch_matches_git(git_module, isolated_project_env: Path):
    branch = git_module.get_current_branch()
    actual = (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=isolated_project_env,
            text=True,
        )
        .strip()
    )
    assert branch == actual


def test_is_clean_working_tree_tracks_changes(git_module, isolated_project_env: Path):
    assert git_module.is_clean_working_tree() is True

    dirty_file = isolated_project_env / "untracked.txt"
    dirty_file.write_text("dirty", encoding="utf-8")
    assert git_module.is_clean_working_tree() is False

    subprocess.run(["git", "add", "-A"], cwd=isolated_project_env, check=True)
    subprocess.run(["git", "commit", "-m", "add file"], cwd=isolated_project_env, check=True)
    assert git_module.is_clean_working_tree() is True


def test_worktree_detection_and_parent(
    git_module, isolated_project_env: Path, tmp_path: Path, monkeypatch
):
    # Create a feature branch worktree
    worktree_path = tmp_path / "wt-feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/one", str(worktree_path)],
        cwd=isolated_project_env,
        check=True,
    )

    # From main repo root → not a worktree, no parent
    assert git_module.is_worktree(path=isolated_project_env) is False
    assert git_module.get_worktree_parent() is None

    # Inside worktree → detect and report parent
    assert git_module.is_worktree(path=worktree_path) is True
    assert git_module.get_worktree_parent(path=worktree_path) == isolated_project_env

    # From within the worktree (no explicit path)
    monkeypatch.chdir(worktree_path)
    assert git_module.is_worktree() is True
    assert git_module.get_worktree_parent() == isolated_project_env
