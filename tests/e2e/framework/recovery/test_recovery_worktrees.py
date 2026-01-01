from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    candidate: Path | None = None
    while cur != cur.parent:
        if (cur / ".git").exists():
            candidate = cur
        cur = cur.parent
    if candidate is None:
        raise RuntimeError("Could not find repository root")
    return candidate


def sh(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = os.environ.copy()
    if env:
        e.update(env)

    # Ensure subprocess can import in-repo `edison` package when executed from tmp dirs.
    src_root = repo_root() / "src"
    existing_py_path = e.get("PYTHONPATH", "")
    e["PYTHONPATH"] = str(src_root) if not existing_py_path else os.pathsep.join([str(src_root), existing_py_path])

    return run_with_timeout(cmd, cwd=cwd, env=e, capture_output=True, text=True)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path
    env = {"AGENTS_PROJECT_ROOT": str(root), "PROJECT_NAME": "example-project"}

    sh(["git", "init", "-b", "main"], cwd=root, env=env)
    (root / "README.md").write_text("test\n", encoding="utf-8")
    sh(["git", "add", "."], cwd=root, env=env)
    sh(["git", "-c", "user.email=ci@example.com", "-c", "user.name=CI", "commit", "-m", "init"], cwd=root, env=env)

    (root / ".project" / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    (root / ".worktrees" / "_archived").mkdir(parents=True, exist_ok=True)
    return root, env


def write_session(root: Path, sid: str) -> None:
    sess_dir = root / ".project" / "sessions" / "wip" / sid
    sess_dir.mkdir(parents=True, exist_ok=True)
    now = iso_now()
    payload = {
        "id": sid,
        "state": "active",
        "phase": "implementation",
        "meta": {
            "sessionId": sid,
            "owner": "tester",
            "createdAt": now,
            "lastActive": now,
            "status": "active",
        },
        "ready": True,
        "git": {"baseBranch": "main", "branchName": None, "worktreePath": None},
        "activityLog": [{"timestamp": now, "message": "Session created"}],
        "tasks": {},
        "qa": {},
    }
    (sess_dir / "session.json").write_text(json.dumps(payload), encoding="utf-8")


def test_clean_worktrees_dry_run_detects_orphans(project: tuple[Path, dict[str, str]]):
    root, env = project
    orphan_sid = "orphan-123"
    orphan_branch = f"session/{orphan_sid}"

    sh(["git", "branch", orphan_branch], cwd=root, env=env)
    wt_dir = root / ".worktrees" / orphan_sid
    sh(["git", "worktree", "add", str(wt_dir), orphan_branch], cwd=root, env=env)

    res = sh(
        [sys.executable, "-m", "edison", "session", "recovery", "clean-worktrees", "--dry-run"],
        cwd=root,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    assert orphan_sid in res.stdout
    assert wt_dir.exists()


def test_clean_worktrees_force_archives_orphans(project: tuple[Path, dict[str, str]]):
    root, env = project

    active_sid = "active-abc"
    write_session(root, active_sid)
    active_branch = f"session/{active_sid}"
    sh(["git", "branch", active_branch], cwd=root, env=env)
    active_wt = root / ".worktrees" / active_sid
    sh(["git", "worktree", "add", str(active_wt), active_branch], cwd=root, env=env)

    orphan_sid = "orphan-xyz"
    orphan_branch = f"session/{orphan_sid}"
    sh(["git", "branch", orphan_branch], cwd=root, env=env)
    orphan_wt = root / ".worktrees" / orphan_sid
    sh(["git", "worktree", "add", str(orphan_wt), orphan_branch], cwd=root, env=env)

    res = sh(
        [sys.executable, "-m", "edison", "session", "recovery", "clean-worktrees", "--force"],
        cwd=root,
        env=env,
    )
    assert res.returncode == 0, res.stderr

    assert active_wt.exists(), "Active session worktree must be preserved"

    archived_dir = root / ".worktrees" / "_archived"
    archived_candidates = list(archived_dir.glob(f"{orphan_sid}*"))
    assert archived_candidates, f"Expected archived entry for {orphan_sid}"
    assert not orphan_wt.exists(), "Orphan worktree should be moved out of the base directory"

