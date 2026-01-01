from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path
import sys

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
    repo = repo_root()
    src_root = repo / "src"
    existing_py_path = e.get("PYTHONPATH", "")
    e["PYTHONPATH"] = str(src_root) if not existing_py_path else os.pathsep.join([str(src_root), existing_py_path])
    return run_with_timeout(argv, cwd=cwd, env=e, capture_output=True, text=True)


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path
    env = {"AGENTS_PROJECT_ROOT": str(root)}
    return root, env


def _make_incomplete_tx(root: Path, sid: str) -> Path:
    base = root / ".project" / "sessions" / "_tx" / sid / "validation"
    tx_dir = base / "1234"
    (tx_dir / "staging").mkdir(parents=True, exist_ok=True)
    (tx_dir / "snapshot").mkdir(parents=True, exist_ok=True)
    meta = {"txId": "1234", "sessionId": sid, "wave": "W3", "startedAt": "2025-01-01T00:00:00Z", "finalizedAt": None, "abortedAt": None}
    (tx_dir / "meta.json").write_text(json.dumps(meta))
    # Dummy files
    (tx_dir / "staging" / "dummy.txt").write_text("x\n")
    (tx_dir / "snapshot" / "y.txt").write_text("y\n")
    return tx_dir


def test_recover_validation_tx_dry_run_lists(project: tuple[Path, dict[str, str]]):
    root, env = project
    sid = "session-x"
    _make_incomplete_tx(root, sid)
    res = run(
        [sys.executable, "-m", "edison", "session", "recovery", "recover-validation-tx", "--dry-run", "--session", sid],
        cwd=root,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    assert "incomplete" in res.stdout.lower()


def test_recover_validation_tx_force_cleans(project: tuple[Path, dict[str, str]]):
    root, env = project
    sid = "session-y"
    tx_dir = _make_incomplete_tx(root, sid)
    res = run(
        [sys.executable, "-m", "edison", "session", "recovery", "recover-validation-tx", "--force", "--session", sid],
        cwd=root,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    # staging and snapshot gone
    assert not (tx_dir / "staging").exists()
    assert not (tx_dir / "snapshot").exists()
