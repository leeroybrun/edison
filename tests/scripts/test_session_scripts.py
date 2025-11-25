import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

EDISON_ROOT = Path(__file__).resolve().parents[2]


def run(domain: str, command: str, args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Execute a CLI command using python -m edison.cli.<domain>.<command>."""
    cmd = [sys.executable, "-m", f"edison.cli.{domain}.{command}", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=EDISON_ROOT,
        check=True,
    )


def make_project_root(tmp_path: Path) -> Path:
    (tmp_path / ".project" / "sessions" / "draft").mkdir(parents=True)
    (tmp_path / ".project" / "sessions" / "active").mkdir(parents=True)
    (tmp_path / ".project" / "sessions" / "validated").mkdir(parents=True)
    (tmp_path / ".project" / "tasks" / "todo").mkdir(parents=True)
    (tmp_path / ".project" / "qa" / "waiting").mkdir(parents=True)
    # Minimal rules/registry to avoid lookup failures
    (tmp_path / "rules").mkdir(parents=True, exist_ok=True)
    (tmp_path / "rules" / "registry.json").write_text(json.dumps({"rules": []}))
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def write_session(root: Path, session_id: str, state: str = "draft") -> Path:
    sess_dir = root / ".project" / "sessions" / state / session_id
    sess_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": session_id,
        "state": state,
        "meta": {
            "sessionId": session_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastActive": datetime.now(timezone.utc).isoformat(),
        },
        "tasks": {},
        "qa": {},
        "activityLog": [],
    }
    (sess_dir / "session.json").write_text(json.dumps(payload))
    return sess_dir


def test_domain_layout_and_no_legacy_wrappers():
    """Ensure new CLI domain folders exist in edison.cli package."""
    cli_dir = EDISON_ROOT / "src" / "edison" / "cli"
    required_dirs = [
        "session",
        "qa",
        "task",
        "rules",
        "config",
        "git",
        "compose",
        "validators",
    ]

    for rel in required_dirs:
        path = cli_dir / rel
        assert path.exists() and path.is_dir(), f"Missing CLI domain folder: {rel}"

    # Verify no legacy scripts directory exists at repo root
    legacy_scripts = EDISON_ROOT / "scripts"
    if legacy_scripts.exists():
        # Scripts dir may exist for migration utilities, but should not contain domain folders
        assert not (legacy_scripts / "session").exists(), "Legacy scripts/session should be removed"
        assert not (legacy_scripts / "tasks").exists(), "Legacy scripts/tasks should be removed"


def test_session_recover_outputs_json(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_session(root, "s1", state="active")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run("session.recovery", "recover", ["--session", "s1", "--json"], env)
    payload = json.loads(proc.stdout.strip())

    rec_path = root / ".project" / "sessions" / "recovery" / "s1"
    assert payload["sessionId"] == "s1"
    assert rec_path.exists()
    assert Path(payload["recoveryPath"]).resolve() == rec_path.resolve()


def test_session_next_returns_json(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_session(root, "alpha")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run("session", "next", ["alpha", "--json", "--limit", "0"], env)
    payload = json.loads(proc.stdout.strip())

    assert payload["sessionId"] == "alpha"
    assert "actions" in payload


def test_session_verify_sets_closing_state(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_session(root, "beta")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run("session", "verify", ["beta", "--phase", "closing", "--json"], env)
    health = json.loads(proc.stdout.strip())

    session_json = root / ".project" / "sessions" / "draft" / "beta" / "session.json"
    data = json.loads(session_json.read_text())
    assert health["ok"] is True
    assert data.get("state") == "closing"


def test_session_close_skip_validation_transitions(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_session(root, "gamma")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run("session", "close", ["gamma", "--skip-validation", "--json"], env)
    payload = json.loads(proc.stdout.strip())

    session_json = root / ".project" / "sessions" / "draft" / "gamma" / "session.json"
    data = json.loads(session_json.read_text())
    assert payload["sessionId"] == "gamma"
    assert data.get("state") == "closing"


def test_session_validate_outputs_json(tmp_path: Path):
    root = make_project_root(tmp_path)
    write_session(root, "delta")
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)

    proc = run("session", "validate", ["delta", "--json"], env)
    payload = json.loads(proc.stdout.strip())

    assert payload["sessionId"] == "delta"
    assert payload.get("validated") is True
