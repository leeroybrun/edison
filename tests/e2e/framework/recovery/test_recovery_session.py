from __future__ import annotations

import os
import json
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


def run(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = os.environ.copy()
    if env:
        e.update(env)
    return run_with_timeout(argv, cwd=cwd, env=e, capture_output=True, text=True)


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path
    env = {"AGENTS_PROJECT_ROOT": str(root)}
    (root / ".project" / "sessions" / "wip").mkdir(parents=True)
    (root / ".project" / "sessions" / "_backup").mkdir(parents=True)
    return root, env


def _write_corrupt_session(root: Path, sid: str) -> Path:
    p = root / ".project" / "sessions" / "wip" / f"{sid}.json"
    p.write_text("{ not-json }\n")
    # Create backup
    (root / ".project" / "sessions" / "_backup" / f"{sid}.json.bak").write_text(
        json.dumps({
            "meta": {"sessionId": sid, "owner": "tester", "mode": "auto", "createdAt": "2025-01-01T00:00:00Z", "lastActive": "2025-01-01T00:00:00Z"},
            "state": "active",
            "tasks": {},
            "qa": {},
            "activityLog": [{"timestamp": "2025-01-01T00:00:00Z", "message": "created"}],
            "git": {},
        })
    )
    return p


def test_repair_session_dry_run_reports_plan(project: tuple[Path, dict[str, str]]):
    root, env = project
    sid = "sess-a"
    _write_corrupt_session(root, sid)
    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "repair-session"
    res = run([str(script), "--dry-run", "--session", sid], cwd=root, env=env)
    assert res.returncode == 0, res.stderr
    out = res.stdout.lower()
    assert "would restore" in out or "plan" in out


def test_repair_session_force_restores_from_backup(project: tuple[Path, dict[str, str]]):
    root, env = project
    sid = "sess-b"
    p = _write_corrupt_session(root, sid)
    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "repair-session"
    res = run([str(script), "--force", "--session", sid], cwd=root, env=env)
    assert res.returncode == 0, res.stderr
    # Should be valid JSON now
    json.loads(p.read_text())