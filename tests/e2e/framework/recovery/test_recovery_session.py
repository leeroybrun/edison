from __future__ import annotations

import json
import os
import subprocess
import sys
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

    # Ensure subprocess can import in-repo `edison` package when executed from tmp dirs.
    src_root = repo_root() / "src"
    existing_py_path = e.get("PYTHONPATH", "")
    e["PYTHONPATH"] = str(src_root) if not existing_py_path else os.pathsep.join([str(src_root), existing_py_path])

    return run_with_timeout(argv, cwd=cwd, env=e, capture_output=True, text=True)


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path
    env = {"AGENTS_PROJECT_ROOT": str(root)}
    (root / ".project" / "sessions" / "wip").mkdir(parents=True)
    return root, env


def _write_corrupt_session(root: Path, sid: str) -> Path:
    sess_dir = root / ".project" / "sessions" / "wip" / sid
    sess_dir.mkdir(parents=True, exist_ok=True)
    p = sess_dir / "session.json"
    p.write_text("{ not-json }\n", encoding="utf-8")
    return p


def test_recover_session_outputs_success(project: tuple[Path, dict[str, str]]):
    root, env = project
    sid = "sess-a"
    _write_corrupt_session(root, sid)
    res = run(
        [sys.executable, "-m", "edison", "session", "recovery", "recover", "--session", sid],
        cwd=root,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    assert "recovered session" in res.stdout.lower()


def test_recover_session_preserves_corrupt_and_writes_valid_json(project: tuple[Path, dict[str, str]]):
    root, env = project
    sid = "sess-b"
    corrupt = _write_corrupt_session(root, sid)

    res = run(
        [sys.executable, "-m", "edison", "session", "recovery", "recover", "--session", sid],
        cwd=root,
        env=env,
    )
    assert res.returncode == 0, res.stderr

    # Session should now be in the recovery directory and have a valid session.json.
    rec_dir = root / ".project" / "sessions" / "recovery" / sid
    session_json = rec_dir / "session.json"
    assert session_json.exists()
    json.loads(session_json.read_text(encoding="utf-8"))

    # Corrupt original should be preserved for forensics.
    assert (rec_dir / "session.json.corrupt").exists()
    assert not corrupt.exists()

