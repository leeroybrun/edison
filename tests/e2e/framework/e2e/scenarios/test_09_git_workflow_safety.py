"""Critical Git Workflow Safety tests (Workstream 9).

Covers:
  - 9.1: Ensure code does NOT modify repo-level signing (commit.gpgsign)
  - 9.2: Ensure worktree creation failures halt and do not claim fake metadata
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from helpers.command_runner import run_script, assert_command_failure, assert_command_success
from helpers.env import TestProjectDir
from edison.core.utils.subprocess import run_with_timeout


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return run_with_timeout(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo_without_touching_gpgsign(repo_root: Path, with_initial_commit: bool = True) -> None:
    # Fresh repo, do NOT set commit.gpgsign globally/locally. Configure identity only.
    cp = _git(repo_root, "init", "-b", "main")
    if cp.returncode != 0:
        raise RuntimeError(f"git init failed: {cp.stderr}")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test User")
    if with_initial_commit:
        (repo_root / "README.md").write_text("# Test Repo\n")
        _git(repo_root, "add", "-A")
        # Use per-command flag to avoid signing prompts without modifying local config
        cp = _git(repo_root, "-c", "commit.gpgsign=false", "commit", "-m", "Initial commit")
        if cp.returncode != 0:
            raise RuntimeError(f"git commit failed: {cp.stderr}")


def _local_config_has_gpgsign_set(cwd: Path) -> bool:
    probe = _git(cwd, "config", "--local", "--get", "commit.gpgsign")
    return probe.returncode == 0 and probe.stdout.strip() != ""


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.edge_case
def test_91_no_repo_level_gpgsign_change(test_project_dir: TestProjectDir):
    """session/new must NOT write commit.gpgsign to repo config; use per-command flags.

    Steps:
      1) Create a repo without setting commit.gpgsign
      2) Run session new (which may commit or create worktree)
      3) Assert commit.gpgsign is NOT set in either repo or worktree
    """
    session_id = "safety-9-1"
    _init_repo_without_touching_gpgsign(test_project_dir.tmp_path, with_initial_commit=True)

    # Sanity: starting state should NOT have commit.gpgsign set
    assert not _local_config_has_gpgsign_set(test_project_dir.tmp_path)

    # Execute real CLI
    result = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(result)

    # After CLI runs, repo-level config must remain untouched
    assert not _local_config_has_gpgsign_set(test_project_dir.tmp_path), (
        "commit.gpgsign MUST NOT be written to local repo config"
    )

    # If a worktree exists, it should not have modified repo-level config either
    sess = test_project_dir.get_session_json(session_id)
    if sess and sess.get("git", {}).get("worktreePath"):
        wt_path = Path(sess["git"]["worktreePath"])
        # Reading with --local in the worktree context still reflects local repo config
        assert not _local_config_has_gpgsign_set(wt_path), (
            "commit.gpgsign MUST NOT be set as a side effect of worktree creation"
        )


@pytest.mark.worktree
@pytest.mark.requires_git
@pytest.mark.edge_case
def test_92_worktree_failure_halts_and_does_not_claim_metadata(test_project_dir: TestProjectDir):
    """If worktree creation fails, `session new` should exit non-zero and not claim a worktree.

    Repro: Use a repo with no initial commit (unborn main) so worktree add fails.
    """
    session_id = "safety-9-2"
    # Initialize repo WITHOUT initial commit → unborn main, worktree add will fail
    _init_repo_without_touching_gpgsign(test_project_dir.tmp_path, with_initial_commit=False)

    result = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    # Expect failure (halt on worktree creation error)
    assert_command_failure(result)

    # No fake git metadata should be persisted
    path = test_project_dir.get_session_path(session_id)
    # Either the session file was not created or it exists without git meta
    if path and path.exists():
        data = json.loads(path.read_text())
        git_meta = data.get("git", {}) if isinstance(data.get("git", {}), dict) else {}
        # Worktree path MUST NOT be claimed on failure
        assert not git_meta.get("worktreePath"), "Session JSON must not claim a worktree on failure"
