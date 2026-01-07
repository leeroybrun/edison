from __future__ import annotations

import os
from pathlib import Path

import pytest

from edison.core.session.worktree.manager.create import create_worktree
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.cache_utils import reset_edison_caches


def _write_yaml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_create_worktree_does_not_fetch_when_start_ref_exists(
    isolated_project_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worktree creation should not block on `git fetch` in the common local-branch case.

    Historically, `create_worktree()` ran `git fetch --all --prune` unconditionally.
    That can hang for a long time on repos with unreachable remotes, even though
    `baseBranchMode=current` uses a local ref that does not require a fetch.
    """
    repo = isolated_project_env

    # Initialize a git repo with a single commit.
    run_with_timeout(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    run_with_timeout(["git", "config", "--local", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    run_with_timeout(["git", "config", "--local", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    run_with_timeout(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    run_with_timeout(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    # Add a remote that would hang if `git fetch` tried to contact it.
    run_with_timeout(["git", "remote", "add", "origin", "ssh://example.invalid/repo.git"], cwd=repo, check=True, capture_output=True)

    # Force `git fetch` to hang deterministically via a fake ssh command.
    fake_ssh = tmp_path / "fake-ssh"
    fake_ssh.write_text("#!/usr/bin/env bash\nsleep 2\nexit 1\n", encoding="utf-8")
    fake_ssh.chmod(0o755)
    monkeypatch.setenv("GIT_SSH_COMMAND", str(fake_ssh))

    # Tighten worktree fetch timeout so any accidental fetch fails quickly in tests.
    _write_yaml(
        repo / ".edison" / "config" / "session.yaml",
        "session:\n"
        "  worktree:\n"
        "    timeouts:\n"
        "      fetch: 1\n",
    )
    # Minimize worktree overhead for this test: avoid meta/shared-state worktree setup
    # and large shared path scans. We only care about fetch behavior.
    _write_yaml(
        repo / ".edison" / "config" / "worktrees.yaml",
        "worktrees:\n"
        "  enabled: true\n"
        "  baseBranchMode: current\n"
        "  sharedState:\n"
        "    mode: primary\n"
        "    sharedPaths: []\n"
        "  installDeps: false\n",
    )
    reset_edison_caches()

    # Ensure we're anchored to this repo root for PathResolver/get_repo_dir.
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    monkeypatch.chdir(repo)

    # If create_worktree unconditionally fetches, this will timeout and fail the test.
    wt_path, branch = create_worktree("sess-skip-fetch", dry_run=False)
    assert wt_path is not None
    assert branch == "session/sess-skip-fetch"
