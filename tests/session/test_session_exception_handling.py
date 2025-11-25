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
if str(SCRIPTS_DIR) not in sys.path:

from edison.core import task  # type: ignore  # noqa: E402
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
            REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json",
            agents_sessions / "TEMPLATE.json",
        )

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

    # Force worktree path and simulate a hard git failure
    class _CalledProcErr(Exception):
        pass

    import subprocess
    err = subprocess.CalledProcessError(returncode=1, cmd=["git", "worktree", "add"], stderr="fatal: boom")

    # Patch config and create_worktree to raise
    with pytest.MonkeyPatch.context() as mp:
        # _load_worktree_config is internal, we might need to patch SessionConfig or just mock create_worktree
        # session_manager.create_session_with_worktree calls session_worktree.create_worktree
        mp.setattr(session_worktree, "create_worktree", lambda *args, **kwargs: (_ for _ in ()).throw(err))

        caplog.set_level("ERROR")
        with pytest.raises(RuntimeError) as exc:
            session_manager.create_session_with_worktree(session_id, owner="tester", mode="auto")

    assert "Session git setup failed" in str(exc.value)
    assert any("Git operation failed" in rec.getMessage() for rec in caplog.records)


def test_permission_error_fails_fast(session_env, caplog):
    """Verify permission errors don't get swallowed and are logged as errors."""
    session_id = "test-perm-denied"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(session_worktree, "create_worktree", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied")))

        caplog.set_level("ERROR")
        with pytest.raises(PermissionError):
            session_manager.create_session_with_worktree(session_id, owner="tester", mode="auto")

    assert any("Permission denied" in rec.getMessage() for rec in caplog.records)


def test_non_critical_errors_logged_but_continue(session_env, caplog):
    """Verify unexpected non-critical errors are logged as warnings and session creation continues."""
    session_id = "test-noncritical"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(session_worktree, "create_worktree", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("flaky env")))

        caplog.set_level("WARNING")
        path = session_manager.create_session_with_worktree(session_id, owner="tester", mode="auto")

    # Session file should exist even after non-critical errors
    assert path.exists()
    assert path.name == f"{session_id}.json"
    assert any("Unexpected git error" in rec.getMessage() for rec in caplog.records)
