from __future__ import annotations

import os
import time
import subprocess
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    raise RuntimeError("Could not find repository root")


def run_cli(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = os.environ.copy()
    if env:
        e.update(env)
    return run_with_timeout(argv, cwd=cwd, env=e, capture_output=True, text=True)


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    # Use isolated project root via AGENTS_PROJECT_ROOT
    root = tmp_path
    env = {"AGENTS_PROJECT_ROOT": str(root)}
    # Minimal project structure
    (root / ".project" / "tasks" / "wip").mkdir(parents=True)
    return root, env


def _touch_old(path: Path, minutes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("")
    old = time.time() - (minutes * 60)
    os.utime(path, (old, old))


def test_clear_locks_dry_run_lists_targets(project: tuple[Path, dict[str, str]]):
    root, env = project
    target = root / ".project" / "tasks" / "wip" / "example.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text("pid=999999\nlockedAt=now\n")
    _touch_old(lock, minutes=120)

    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "clear-locks"
    res = run_cli([str(script), "--dry-run", "--max-age", "60"], cwd=root, env=env)
    assert res.returncode == 0, res.stderr
    assert "stale" in res.stdout.lower()
    assert str(lock.relative_to(root)) in res.stdout
    assert lock.exists(), "Dry run must not delete"


def test_clear_locks_force_removes_old_dead_locks(project: tuple[Path, dict[str, str]]):
    root, env = project
    target = root / ".project" / "tasks" / "wip" / "old-dead.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text("pid=999999\nlockedAt=now\n")
    _touch_old(lock, minutes=90)

    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "clear-locks"
    res = run_cli([str(script), "--force", "--max-age", "60"], cwd=root, env=env)
    assert res.returncode == 0, res.stderr
    assert not lock.exists(), "--force should remove stale dead lock"


def test_clear_locks_preserves_active_pid(project: tuple[Path, dict[str, str]]):
    root, env = project
    target = root / ".project" / "tasks" / "wip" / "active.md"
    target.write_text("dummy\n")
    lock = target.with_suffix(".md.lock")
    lock.write_text(f"pid={os.getpid()}\nlockedAt=now\n")
    _touch_old(lock, minutes=180)

    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "clear-locks"
    res = run_cli([str(script), "--force", "--max-age", "60"], cwd=root, env=env)
    assert res.returncode == 0, res.stderr
    assert lock.exists(), "Active PID lock must be preserved"