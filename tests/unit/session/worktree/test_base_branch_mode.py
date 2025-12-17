from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest
import yaml


def _git(cwd: Path, *args: str) -> str:
    return (
        subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    )


def _write_worktrees_config(repo_root: Path, data: dict) -> None:
    cfg_dir = repo_root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(yaml.safe_dump(data), encoding="utf-8")


def _reset_worktree_caches() -> None:
    from edison.core.config.cache import clear_all_caches
    from edison.core.session._config import reset_config_cache
    from tests.helpers.env_setup import clear_path_caches

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()


def test_base_branch_mode_current_uses_primary_head_and_does_not_switch_primary_branch(
    session_git_repo_path: Path, tmp_path: Path
) -> None:
    from edison.core.session import worktree

    repo = session_git_repo_path

    # Create and checkout a feature branch with a unique commit.
    _git(repo, "checkout", "-b", "feature/base-mode")
    (repo / "feature.txt").write_text("feature", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "feature commit")

    primary_branch_before = _git(repo, "branch", "--show-current")
    primary_head_before = _git(repo, "rev-parse", "HEAD")

    _write_worktrees_config(
        repo,
        {
            "worktrees": {
                "enabled": True,
                "baseBranchMode": "current",
                "baseBranch": None,
                "baseDirectory": str(tmp_path / "worktrees"),
                "archiveDirectory": str(tmp_path / "worktrees" / "_archived"),
                "branchPrefix": "session/",
            }
        },
    )
    _reset_worktree_caches()

    wt_path, wt_branch = worktree.create_worktree("sess-current-mode")
    assert wt_path is not None
    assert wt_branch == "session/sess-current-mode"

    # Worktree starts from the current primary HEAD commit.
    assert _git(wt_path, "rev-parse", "HEAD") == primary_head_before

    # Primary worktree branch must not be switched by worktree creation.
    assert _git(repo, "branch", "--show-current") == primary_branch_before


def test_base_branch_mode_fixed_uses_configured_branch_even_when_primary_on_feature(
    session_git_repo_path: Path, tmp_path: Path
) -> None:
    from edison.core.session import worktree

    repo = session_git_repo_path
    main_head_before = _git(repo, "rev-parse", "HEAD")

    # Create a feature branch with a unique commit and switch primary to it.
    _git(repo, "checkout", "-b", "feature/fixed-mode")
    (repo / "feature2.txt").write_text("feature2", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "feature2 commit")
    feature_head = _git(repo, "rev-parse", "HEAD")
    assert feature_head != main_head_before

    _write_worktrees_config(
        repo,
        {
            "worktrees": {
                "enabled": True,
                "baseBranchMode": "fixed",
                "baseBranch": "main",
                "baseDirectory": str(tmp_path / "worktrees2"),
                "archiveDirectory": str(tmp_path / "worktrees2" / "_archived"),
                "branchPrefix": "session/",
            }
        },
    )
    _reset_worktree_caches()

    wt_path, wt_branch = worktree.create_worktree("sess-fixed-mode")
    assert wt_path is not None
    assert wt_branch == "session/sess-fixed-mode"

    # Worktree starts from configured base branch (main), not the current feature branch.
    assert _git(wt_path, "rev-parse", "HEAD") == main_head_before
    assert _git(repo, "branch", "--show-current") == "feature/fixed-mode"
