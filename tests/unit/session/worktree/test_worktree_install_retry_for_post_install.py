from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from edison.core.config.cache import clear_all_caches
from edison.core.session import worktree
from edison.core.session._config import reset_config_cache
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.env_setup import clear_path_caches


@pytest.fixture(autouse=True)
def setup_worktree_config(session_git_repo_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_dir = session_git_repo_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    worktrees_dir = session_git_repo_path / "worktrees"

    session_data = {
        "worktrees": {
            "enabled": True,
            "baseDirectory": str(worktrees_dir),
            "branchPrefix": "session/",
            "sharedState": {
                "mode": "meta",
                "metaBranch": "edison-meta",
                "metaPathTemplate": str(worktrees_dir / "_meta"),
            },
            "timeouts": {
                "health_check": 2,
                "fetch": 5,
                "worktree_add": 5,
                "install": 10,
                "branch_check": 5,
            },
            # Fails unless the install step created the marker file.
            "postInstallCommands": ["test -f .edison-test-install-ok"],
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data), encoding="utf-8")

    monkeypatch.setenv("PROJECT_NAME", "testproj")

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    yield

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()


def _install_fake_pnpm(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    pnpm_path = bin_dir / "pnpm"
    pnpm_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "$@" >> "${EDISON_TEST_PNPM_LOG}"

if [[ "$*" == "install" ]]; then
  echo "ok" > .edison-test-install-ok
fi

exit 0
""",
        encoding="utf-8",
    )
    pnpm_path.chmod(0o755)


def test_post_install_failure_retries_with_non_immutable_install(
    session_git_repo_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (session_git_repo_path / "package.json").write_text('{"name":"x","private":true}\n', encoding="utf-8")
    (session_git_repo_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9.0\n", encoding="utf-8")
    run_with_timeout(["git", "add", "package.json", "pnpm-lock.yaml"], cwd=session_git_repo_path, check=True)
    run_with_timeout(["git", "commit", "-m", "add pnpm lockfile"], cwd=session_git_repo_path, check=True)

    log_path = tmp_path / "pnpm.log"
    log_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("EDISON_TEST_PNPM_LOG", str(log_path))

    fake_bin = tmp_path / "bin"
    _install_fake_pnpm(fake_bin)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    base_branch = (
        run_with_timeout(
            ["git", "branch", "--show-current"],
            cwd=session_git_repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
    )

    sid = "install-retry"
    wt_path, branch = worktree.create_worktree(sid, base_branch=base_branch, install_deps=True)
    assert wt_path is not None

    try:
        recorded = log_path.read_text(encoding="utf-8").splitlines()
        assert any("install --frozen-lockfile" in line for line in recorded)
        assert any(line.strip() == "install" for line in recorded)
        assert (wt_path / ".edison-test-install-ok").exists()
    finally:
        worktree.cleanup_worktree(sid, wt_path, branch, delete_branch=True)
