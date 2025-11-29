from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from tests.helpers.paths import get_repo_root

CORE_DIR = get_repo_root()
SCRIPTS_DIR = CORE_DIR / "scripts" / "git"

# Helper to run CLI commands using python -m
def _run_cli(module: str, args: list[str], repo: Path) -> subprocess.CompletedProcess:
    """Run a CLI command using python -m syntax."""
    cmd = [sys.executable, "-m", module] + args
    return subprocess.run(
        cmd,
        cwd=repo,
        env=_create_env(repo),
        capture_output=True,
        text=True
    )


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

    cfg_dir = repo / ".edison" / "core" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    defaults = textwrap.dedent(
        """
        worktrees:
          enabled: true
          baseDirectory: .worktrees
          archiveDirectory: .worktrees/_archived
          branchPrefix: session/
          baseBranch: main
          installDeps: false
        session:
          worktree:
            timeouts:
              health_check: 5
              fetch: 5
              checkout: 5
              worktree_add: 5
              clone: 5
              install: 5
        cli:
          json:
            indent: 2
            sort_keys: true
            ensure_ascii: false
        """
    )
    (cfg_dir / "defaults.yaml").write_text(defaults)
    # Seed an initial commit so real git worktree operations can run
    (repo / "README.md").write_text("# test repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def _create_create_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(repo)
    return env


def test_worktree_create_dry_run_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    args = [
        "sess-123",
        "--dry-run",
        "--json",
        "--repo-root",
        str(repo),
    ]
    result = _run_cli("edison.cli.git.worktree_create", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["sessionId"] == "sess-123"
    # baseDirectory is relative to repo parent
    assert Path(data["path"]).resolve() == (repo.parent / ".worktrees" / "sess-123").resolve()
    assert data["dryRun"] is True


def test_worktree_archive_dry_run_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    wt = repo.parent / ".worktrees" / "sess-123"
    wt.mkdir(parents=True, exist_ok=True)

    args = [
        "sess-123",
        "--dry-run",
        "--json",
        "--repo-root",
        str(repo),
    ]
    result = _run_cli("edison.cli.git.worktree_archive", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["sessionId"] == "sess-123"
    assert Path(data["archivedPath"]).resolve() == (
        repo.parent / ".worktrees" / "_archived" / "sess-123"
    ).resolve()
    assert data["dryRun"] is True


def test_worktree_cleanup_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    args = [
        "--dry-run",
        "--json",
        "--repo-root",
        str(repo),
    ]
    result = _run_cli("edison.cli.git.worktree_cleanup", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["dryRun"] is True
    assert data["status"] == "ok"
