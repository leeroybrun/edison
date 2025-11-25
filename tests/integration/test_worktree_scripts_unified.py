from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest


CORE_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = CORE_DIR / "scripts" / "git"


def _repo_with_worktree_config(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("# unified worktrees\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    cfg_dir = repo / ".edison" / "core" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = textwrap.dedent(
        """
        worktrees:
          enabled: true
          baseDirectory: .wt-base
          archiveDirectory: .wt-archive
          branchPrefix: unified/
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
        """
    ).strip()
    (cfg_dir / "defaults.yaml").write_text(cfg + "\n", encoding="utf-8")
    return repo


def _env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(repo)
    return env


@pytest.mark.requires_git
def test_worktree_scripts_use_session_worktree_and_new_schema(tmp_path: Path) -> None:
    repo = _repo_with_worktree_config(tmp_path)
    env = _env(repo)

    session_id = "sess-unified"
    expected_wt_path = (repo.parent / ".wt-base" / session_id).resolve()
    expected_archive = (repo.parent / ".wt-archive" / session_id).resolve()
    expected_branch = f"unified/{session_id}"

    # Create worktree (real git operations, no mocks)
    create_cmd = [
        str(SCRIPTS_DIR / "worktree-create"),
        session_id,
        "--json",
        "--repo-root",
        str(repo),
    ]
    create = subprocess.run(create_cmd, cwd=repo, env=env, capture_output=True, text=True)
    assert create.returncode == 0, create.stderr
    payload = json.loads(create.stdout)
    assert Path(payload["path"]).resolve() == expected_wt_path

    # Verify branch and worktree registered via git
    branches = subprocess.run(
        ["git", "branch", "--list", expected_branch],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert expected_branch in branches.stdout

    wt_list = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert str(expected_wt_path) in wt_list.stdout

    # Archive the worktree using the CLI and new config
    archive_cmd = [
        str(SCRIPTS_DIR / "worktree-archive"),
        session_id,
        "--json",
        "--repo-root",
        str(repo),
    ]
    archive = subprocess.run(archive_cmd, cwd=repo, env=env, capture_output=True, text=True)
    assert archive.returncode == 0, archive.stderr
    archived_payload = json.loads(archive.stdout)
    assert Path(archived_payload["archivedPath"]).resolve() == expected_archive
    assert expected_archive.exists()

    # Cleanup/prune should succeed with the same schema
    cleanup_cmd = [
        str(SCRIPTS_DIR / "worktree-cleanup"),
        "--json",
        "--repo-root",
        str(repo),
    ]
    cleanup = subprocess.run(cleanup_cmd, cwd=repo, env=env, capture_output=True, text=True)
    assert cleanup.returncode == 0, cleanup.stderr
    cleanup_payload = json.loads(cleanup.stdout)
    assert cleanup_payload["status"] == "ok"

    # After archive + cleanup, worktree should no longer be registered
    wt_list_after = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert str(expected_wt_path) not in wt_list_after.stdout

