"""Workstream 7: Git Workflow Centralization (TDD)

Tests cover:
- Base branch loaded from manifest config
- Duplicate worktree detection (reuse existing worktree for branch)
- Archival listing sorted by timestamp (most recent first)
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
)
from helpers.env import TestProjectDir
from edison.core.utils.subprocess import run_with_timeout


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return run_with_timeout(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_git_repo(repo_root: Path, base_branch: str = "main") -> None:
    cp = _run_git(repo_root, "init", "-b", base_branch)
    run_with_timeout(["git", "config", "--local", "commit.gpgsign", "false"], cwd=repo_root, check=True, capture_output=True)
    if cp.returncode != 0:
        raise RuntimeError(f"git init failed: {cp.stderr}")
    _run_git(repo_root, "config", "user.email", "test@example.com")
    _run_git(repo_root, "config", "user.name", "Test User")
    (repo_root / "README.md").write_text("# Test Repo\n")
    _run_git(repo_root, "add", "-A")
    cp = _run_git(repo_root, "commit", "-m", "Initial commit")
    if cp.returncode != 0:
        raise RuntimeError(f"git commit failed: {cp.stderr}")


@pytest.mark.worktree
@pytest.mark.requires_git
def test_base_branch_loaded_from_manifest(project_dir: TestProjectDir, tmp_path: Path):
    """session new should respect worktrees.baseBranch from manifest."""
    # Patch manifest baseBranch to 'develop'
    manifest_path = project_dir.edison_root / "manifest.json"
    assert manifest_path.exists(), "manifest.json must exist in test env"
    manifest = json.loads(manifest_path.read_text())
    manifest.setdefault("worktrees", {})["baseBranchMode"] = "fixed"
    manifest.setdefault("worktrees", {})["baseBranch"] = "develop"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Init repo on 'develop'
    _init_git_repo(project_dir.tmp_path, base_branch="develop")

    sid = "ws7-base-branch"
    res = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", sid, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(res)

    # Verify session JSON records baseBranch from config (develop), not hardcoded 'main'
    sess_json = project_dir.get_session_json(sid)
    assert sess_json["git"]["baseBranch"] == "develop"


@pytest.mark.worktree
@pytest.mark.requires_git
def test_duplicate_worktree_detection_prefers_existing_path(project_dir: TestProjectDir):
    """If a worktree for session branch already exists elsewhere, CLI/library should reuse it."""
    _init_git_repo(project_dir.tmp_path)

    sid = "ws7-dup-check"
    branch = f"session/{sid}"

    # Manually create a worktree in a non-standard location first
    existing_dir = project_dir.tmp_path / "custom-wt" / sid
    existing_dir.parent.mkdir(parents=True, exist_ok=True)
    cp = _run_git(project_dir.tmp_path, "worktree", "add", "-b", branch, str(existing_dir), "main")
    if cp.returncode != 0:
        raise RuntimeError(f"Failed to create pre-existing worktree: {cp.stderr}")

    # Now run REAL CLI to create session; it must detect and attach to existing worktree
    res = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", sid, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(res)

    sess_json = project_dir.get_session_json(sid)
    assert Path(sess_json["git"]["worktreePath"]).resolve() == existing_dir.resolve()


@pytest.mark.fast
def test_archival_listing_sorted_by_mtime(project_dir: TestProjectDir):
    """session status (markdown) lists archived worktrees in deterministic order (newest first)."""
    # Prepare fake archive directory with 3 entries.
    #
    # The CLI subprocess forces PROJECT_NAME="example-project" for determinism (see helpers/command_runner.py),
    # and core defaults place worktrees under the repo root: .worktrees/_archived.
    archive_root = project_dir.tmp_path / ".worktrees" / "_archived"
    archive_root.mkdir(parents=True, exist_ok=True)
    a = archive_root / "a"
    b = archive_root / "b"
    c = archive_root / "c"
    for d in [a, b, c]:
        d.mkdir(parents=True, exist_ok=True)
    # Set mtimes: c newest, then a, then b
    now = time.time()
    os.utime(a, (now - 50, now - 50))
    os.utime(b, (now - 100, now - 100))
    os.utime(c, (now - 10, now - 10))

    # Create a minimal session so `session status` runs
    _init_git_repo(project_dir.tmp_path)
    sid = "ws7-archive-order"
    res = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", sid, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(res)

    status = run_script("session", ["status", sid], cwd=project_dir.tmp_path)
    assert_command_success(status)
    out = status.stdout
    # Expect an "Archived Worktrees" section with c, a, b order
    start = out.find("## Archived Worktrees")
    assert start != -1, f"Archived Worktrees section missing. Output was:\n{out}"
    section = out[start:]
    order = [line.strip("- ") for line in section.splitlines() if line.strip().startswith("- ")][:3]
    assert order == [str(c), str(a), str(b)]
