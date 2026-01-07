from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

from edison.core.qa.engines.registry import EngineRegistry
from edison.core.utils.io.locking import acquire_file_lock
from edison.core.web_server import web_server_lock_path


def _write_validation_config(repo_root: Path, yaml_text: str) -> None:
    cfg_dir = repo_root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(yaml_text, encoding="utf-8")


@pytest.mark.requires_git
@pytest.mark.worktree
@pytest.mark.slow
def test_web_server_lock_uses_worktree_parent_repo_root(
    isolated_project_env: Path,
) -> None:
    """Cross-session locks must be shared across git worktrees (parent repo root)."""
    lock_key = "test-worktree-parent-lock"

    _write_validation_config(
        isolated_project_env,
        f"""
validation:
  defaults:
    web_server:
      lock:
        enabled: true
        key: "{lock_key}"
        scope: repo
      probe_timeout_seconds: 0.2
      poll_interval_seconds: 0.05
  validators:
    test-web:
      name: "Test Web Validator"
      engine: pal-mcp
      wave: comprehensive
      blocking: true
      always_run: true
      web_server:
        url: "http://127.0.0.1:1"
""".lstrip(),
    )

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=str(isolated_project_env),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    # Initialize the repo as a real git checkout so worktree detection works.
    _git("init", "-b", "main")
    _git("config", "--local", "user.email", "test@example.com")
    _git("config", "--local", "user.name", "Test User")
    _git("config", "--local", "commit.gpgsign", "false")
    _git("add", "-A")
    _git("commit", "-m", "init")

    worktree_path = isolated_project_env / ".worktrees" / "S001"
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", str(worktree_path), "-b", "session/S001", "main")

    lock_path = web_server_lock_path(repo_root=isolated_project_env, key=lock_key, scope="repo")

    registry = EngineRegistry(project_root=worktree_path)
    done = {"flag": False}

    def _run() -> None:
        registry.run_validator(
            validator_id="test-web",
            task_id="T001",
            session_id="S001",
            worktree_path=worktree_path,
        )
        done["flag"] = True

    with acquire_file_lock(lock_path, timeout=3.0, repo_root=isolated_project_env):
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        time.sleep(0.3)
        assert done["flag"] is False

    t.join(timeout=15.0)
    assert done["flag"] is True


def test_web_server_lock_global_scope_uses_user_config_dir(
    isolated_project_env: Path,
) -> None:
    user_root = Path(os.environ["EDISON_paths__user_config_dir"]).expanduser().resolve()
    lock_key = "test-global-lock"

    lock_path = web_server_lock_path(repo_root=isolated_project_env, key=lock_key, scope="global")

    expected = (user_root / "_locks" / "web_server" / lock_key).resolve()
    assert lock_path == expected
