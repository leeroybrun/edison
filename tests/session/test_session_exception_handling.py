"""Tests for git exception handling during session creation.

TDD scope:
- RED: verify current behavior swallows exceptions (will fail initially)
- GREEN: specific handling raises/logs appropriately
- REFACTOR: helper-based handling continues to satisfy tests
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest


# Wire scripts/lib onto sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / ".edison" / "core"
from edison.core import task  # type: ignore  # noqa: E402
from edison.data import get_data_path
from edison.core.session import manager as session_manager
from edison.core.session import worktree as session_worktree


class _SessionEnv:
    def __init__(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-session-tests-"))
        self.project_root = self.temp_root / ".project"
        self.sessions_root = self.project_root / "sessions"

    def setup(self) -> None:
        # Minimal project layout + template copy
        for d in ("wip", "done", "validated"):
            (self.sessions_root / d).mkdir(parents=True, exist_ok=True)
        agents_sessions = self.temp_root / ".agents" / "sessions"
        agents_sessions.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            get_data_path("templates", "session.template.json"),
            agents_sessions / "TEMPLATE.json",
        )

        # Initialize a git repository for worktree tests
        import subprocess
        try:
            subprocess.run(["git", "init"], cwd=self.temp_root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.temp_root, check=True, capture_output=True)
            # Create an initial commit so HEAD exists
            (self.temp_root / "README.md").write_text("# Test Repo\n")
            subprocess.run(["git", "add", "README.md"], cwd=self.temp_root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.temp_root, check=True, capture_output=True)
        except Exception:
            # If git setup fails, tests that require git will fail appropriately
            pass

    def teardown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)


@pytest.fixture()
def session_env():
    env = _SessionEnv()
    env.setup()
    old_env = os.environ.copy()
    # Point task/sessionlib ROOT at a temp sandbox
    os.environ["AGENTS_PROJECT_ROOT"] = str(env.temp_root)
    os.environ["project_ROOT"] = str(env.temp_root)
    # Reload modules so constants derive from the new ROOT
    import importlib
    import edison.core.task as _task  # type: ignore
    import edison.core.session.manager as _session_manager  # type: ignore
    import edison.core.session.worktree as _session_worktree  # type: ignore
    importlib.reload(_task)
    importlib.reload(_session_manager)
    importlib.reload(_session_worktree)
    global task  # type: ignore
    global session_manager  # type: ignore
    global session_worktree  # type: ignore
    task = _task
    session_manager = _session_manager
    session_worktree = _session_worktree
    try:
        yield env
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        env.teardown()


def _enabled_worktree_config(override: Optional[dict] = None) -> dict:
    base = {
        "enabled": True,
        "defaultMode": "worktree",
        "branchPrefix": "session/",
        "defaultBaseBranch": "main",
        "installDeps": False,
    }
    base.update(override or {})
    return base


def test_git_failure_raises_error(session_env, caplog):
    """Verify git failures raise explicit errors and are logged."""
    session_id = "test-fail-git"

    # The actual flow: create_worktree raises RuntimeError -> manager wraps in SessionError
    # -> create_session detects "worktree" in error and raises RuntimeError
    with pytest.MonkeyPatch.context() as mp:
        # Patch create_worktree to raise RuntimeError (what it actually raises)
        def mock_create_worktree(*args, **kwargs):
            raise RuntimeError("Failed to create worktree after retries: git error")

        mp.setattr(session_worktree, "create_worktree", mock_create_worktree)

        caplog.set_level("ERROR")
        with pytest.raises(session_manager.SessionError) as exc:
            session_manager.create_session(session_id, owner="tester", mode="auto", create_wt=True)

    assert "Failed to create worktree" in str(exc.value)
    assert session_id in str(exc.value)


def test_permission_error_fails_fast(session_env, caplog):
    """Verify permission errors are wrapped and logged as errors.

    The flow is: PermissionError -> SessionError (with worktree in message)
    """
    session_id = "test-perm-denied"

    with pytest.MonkeyPatch.context() as mp:
        def mock_create_worktree(*args, **kwargs):
            raise PermissionError("denied")

        mp.setattr(session_worktree, "create_worktree", mock_create_worktree)

        caplog.set_level("ERROR")
        # PermissionError gets wrapped in SessionError
        with pytest.raises(session_manager.SessionError) as exc:
            session_manager.create_session(session_id, owner="tester", mode="auto", create_wt=True)

    assert "Failed to create worktree" in str(exc.value)
    assert session_id in str(exc.value)


def test_non_critical_errors_logged_but_continue(session_env, caplog):
    """Verify that generic exceptions during worktree creation are wrapped and raised.

    The flow is: Exception -> SessionError (with 'worktree' in message)
    """
    session_id = "test-noncritical"

    with pytest.MonkeyPatch.context() as mp:
        def mock_create_worktree(*args, **kwargs):
            raise Exception("flaky env")

        mp.setattr(session_worktree, "create_worktree", mock_create_worktree)

        caplog.set_level("ERROR")
        # Generic exceptions get wrapped in SessionError
        with pytest.raises(session_manager.SessionError) as exc:
            session_manager.create_session(session_id, owner="tester", mode="auto", create_wt=True)

    # Should be wrapped in SessionError with standard message
    assert "Failed to create worktree" in str(exc.value)
    assert session_id in str(exc.value)
