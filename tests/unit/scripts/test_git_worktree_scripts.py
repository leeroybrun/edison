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

    cfg_dir = repo / ".edison" / "config"
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


def _make_repo_with_worktrees_enabled(tmp_path: Path, *, enabled: bool) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    defaults = textwrap.dedent(
        f"""
        worktrees:
          enabled: {str(enabled).lower()}
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


def _create_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(repo)
    return env


def test_worktree_create_dry_run_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    args = [
        "sess-123",
        "--dry-run",
        "--json",
    ]
    result = _run_cli("edison.cli.git.worktree_create", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["session_id"] == "sess-123"
    # baseDirectory is anchored to the repo root (use `../...` in config to escape).
    assert Path(data["worktree_path"]).resolve() == (repo / ".worktrees" / "sess-123").resolve()
    assert data["dry_run"] is True


def test_worktree_create_fails_when_worktrees_disabled(tmp_path: Path) -> None:
    repo = _make_repo_with_worktrees_enabled(tmp_path, enabled=False)
    args = [
        "sess-123",
        "--json",
    ]
    result = _run_cli("edison.cli.git.worktree_create", args, repo)
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert err["error"] == "worktree_create_error"


def test_worktree_create_honors_path_override_in_dry_run(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    override = str(repo.parent / "custom-worktrees" / "sess-123")
    args = [
        "sess-123",
        "--dry-run",
        "--path",
        override,
        "--json",
    ]
    result = _run_cli("edison.cli.git.worktree_create", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert Path(data["worktree_path"]).resolve() == Path(override).resolve()


def test_worktree_create_updates_session_git_metadata_when_session_exists(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    session_id = "sess-123"
    sess_repo = SessionRepository(project_root=repo)
    sess_repo.create(Session.create(session_id, owner="test", state="active"))

    args = [
        session_id,
        "--json",
    ]
    result = _run_cli("edison.cli.git.worktree_create", args, repo)
    assert result.returncode == 0, result.stderr

    sess = sess_repo.get(session_id)
    assert sess is not None
    git_meta = sess.to_dict().get("git", {})
    assert git_meta.get("worktreePath")
    assert git_meta.get("branchName") == f"session/{session_id}"


def test_worktree_create_fails_fast_when_session_already_linked_to_other_worktree(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    session_id = "sess-123"
    other = str(repo.parent / "other-worktrees" / session_id)
    sess = Session.create(session_id, owner="test", state="active")
    data = sess.to_dict()
    data.setdefault("git", {})["worktreePath"] = other
    sess_repo = SessionRepository(project_root=repo)
    sess_repo.create(Session.from_dict(data))

    # Should fail before doing any worktree changes.
    args = [
        session_id,
        "--dry-run",
        "--json",
    ]
    result = _run_cli("edison.cli.git.worktree_create", args, repo)
    assert result.returncode != 0
    err = json.loads(result.stderr)
    assert err["error"] == "worktree_create_error"

    # `--force` allows overriding the linkage check.
    args_force = [
        session_id,
        "--dry-run",
        "--force",
        "--json",
    ]
    result_force = _run_cli("edison.cli.git.worktree_create", args_force, repo)
    assert result_force.returncode == 0, result_force.stderr


def test_worktree_archive_dry_run_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    wt = repo / ".worktrees" / "sess-123"
    wt.mkdir(parents=True, exist_ok=True)

    args = [
        "sess-123",
        "--dry-run",
        "--json",
    ]
    result = _run_cli("edison.cli.git.worktree_archive", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["session_id"] == "sess-123"
    assert Path(data["archived_path"]).resolve() == (
        repo / ".worktrees" / "_archived" / "sess-123"
    ).resolve()
    assert data["dry_run"] is True


def test_worktree_cleanup_json(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    # Create a real worktree first (so cleanup has a valid target to remove)
    create_args = ["sess-123", "--json"]
    create_result = _run_cli("edison.cli.git.worktree_create", create_args, repo)
    assert create_result.returncode == 0, create_result.stderr

    args = ["sess-123", "--json"]
    result = _run_cli("edison.cli.git.worktree_cleanup", args, repo)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["session_id"] == "sess-123"
    assert data["deleted_branch"] is False


def test_worktree_restore_honors_source_override_in_dry_run(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    session_id = "sess-123"

    # Create a fake archive directory for this session under a custom root.
    custom_archive_root = repo.parent / "custom-archive"
    (custom_archive_root / session_id).mkdir(parents=True, exist_ok=True)

    # Without --source, restore should fail because default archive doesn't exist.
    args_fail = [
        session_id,
        "--dry-run",
        "--json",
    ]
    res_fail = _run_cli("edison.cli.git.worktree_restore", args_fail, repo)
    assert res_fail.returncode != 0

    # With --source, restore should succeed in dry-run mode.
    args_ok = [
        session_id,
        "--dry-run",
        "--source",
        str(custom_archive_root),
        "--json",
    ]
    res_ok = _run_cli("edison.cli.git.worktree_restore", args_ok, repo)
    assert res_ok.returncode == 0, res_ok.stderr
