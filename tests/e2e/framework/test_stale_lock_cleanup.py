from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

# Add tests directory to path so tests can import from helpers.*
TESTS_ROOT = Path(__file__).resolve().parent.parent.parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from helpers.command_runner import run_script, assert_command_success
from helpers.env import TestProjectDir


@pytest.fixture()
def project(tmp_path: Path) -> TestProjectDir:
    def get_repo_root() -> Path:
        current = Path(__file__).resolve()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find repository root")

    repo_root = get_repo_root()
    return TestProjectDir(tmp_path, repo_root)


def _touch_old(path: Path, minutes: int) -> None:
    """Set mtime to now - minutes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("")
    old = time.time() - (minutes * 60)
    os.utime(path, (old, old))


def _run_cleanup(project: TestProjectDir, max_age: int = 60):
    return run_script(
        "tasks/cleanup-stale-locks",
        ["--max-age", str(max_age)],
        cwd=project.tmp_path,
        check=False,
    )


def test_stale_lock_cleanup_removes_old_locks(project: TestProjectDir):
    """Verify cleanup removes locks > max_age with dead process."""
    target = project.project_root / "tasks" / "wip" / "dead-lock.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text("pid=999999\nlockedAt=now\n")  # pid unlikely to exist
    _touch_old(lock, minutes=120)  # 2 hours old

    res = _run_cleanup(project, max_age=60)
    assert_command_success(res)
    assert not lock.exists(), "Old dead lock should be removed"


def test_active_lock_not_removed(project: TestProjectDir):
    """Verify active locks are preserved (PID alive)."""
    mypid = os.getpid()
    target = project.project_root / "tasks" / "wip" / "active-lock.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text(f"pid={mypid}\nlockedAt=now\n")
    _touch_old(lock, minutes=180)  # very old but process is alive

    res = _run_cleanup(project, max_age=60)
    assert_command_success(res)
    assert lock.exists(), "Active lock should not be removed"


def test_recent_lock_not_removed(project: TestProjectDir):
    """Verify recent locks are preserved even with dead PID."""
    target = project.project_root / "tasks" / "wip" / "recent-dead.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text("pid=424242\nlockedAt=now\n")
    _touch_old(lock, minutes=5)  # too recent

    res = _run_cleanup(project, max_age=60)
    assert_command_success(res)
    assert lock.exists(), "Recent lock should not be removed"


def test_cleanup_handles_invalid_lock_files(project: TestProjectDir):
    """Verify cleanup handles corrupted lock files gracefully (old invalid)."""
    target = project.project_root / "tasks" / "wip" / "invalid-lock.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text("this is not a pid\n")
    _touch_old(lock, minutes=180)

    res = _run_cleanup(project, max_age=60)
    assert_command_success(res)
    assert not lock.exists(), "Old invalid lock should be removed"
