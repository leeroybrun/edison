"""Session timeout enforcement tests (WP-002).

Validates:
- Expired sessions are detectable and cleanable via `edison session cleanup-expired`
- Claiming into an expired session is fail-closed
- Timestamp parsing handles Z and +00:00 variants
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import pytest
import yaml

from edison.core.utils.subprocess import run_with_timeout
from tests.config import get_default_value
from tests.e2e.base import create_project_structure, copy_templates, setup_base_environment
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()
TIMEOUT_HOURS = int(get_default_value("timeouts", "session_timeout_hours"))
SKEW_ALLOWANCE_SECONDS = int(get_default_value("timeouts", "clock_skew_allowance_seconds"))


def _write_iso(dt: datetime, tz_variant: str = "Z") -> str:
    ts = dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    if tz_variant == "Z":
        return ts.replace("+00:00", "Z")
    return ts


@pytest.fixture
def session_timeout_env(tmp_path: Path) -> Generator[dict, None, None]:
    """Set up isolated test environment for session timeout tests."""
    create_project_structure(tmp_path)
    copy_templates(tmp_path)
    env = setup_base_environment(tmp_path, owner="codex-pid-9999")

    # Provide deterministic recovery settings for timeout tests.
    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "session.yml").write_text(
        yaml.safe_dump(
            {
                "session": {
                    "recovery": {
                        "timeoutHours": TIMEOUT_HOURS,
                        "clockSkewAllowanceSeconds": SKEW_ALLOWANCE_SECONDS,
                        "defaultTimeoutMinutes": TIMEOUT_HOURS * 60,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    # Ensure the subprocess can import the in-repo `edison` package.
    src_root = REPO_ROOT / "src"
    existing_py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(src_root), existing_py_path] if existing_py_path else [str(src_root)])

    yield {
        "root": tmp_path,
        "project_root": tmp_path / ".project",
        "env": env,
    }


def run_cli(env_data: dict, *argv: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Execute `python -m edison` with the E2E env."""
    cmd = [sys.executable, "-m", "edison"] + [str(a) for a in argv]
    res = run_with_timeout(cmd, cwd=REPO_ROOT, env=env_data["env"], capture_output=True, text=True)
    if check and res.returncode != 0:
        raise AssertionError(
            f"Command failed ({res.returncode})\nCMD: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res


def task_id(slot: int, wave: str, slug: str) -> str:
    return f"{slot}-{wave}-{slug}"


def create_task(env_data: dict, slot: int, wave: str, slug: str) -> str:
    tid = task_id(slot, wave, slug)
    run_cli(
        env_data,
        "task",
        "new",
        "--id",
        str(slot),
        "--wave",
        wave,
        "--slug",
        slug,
        "--repo-root",
        str(env_data["root"]),
    )
    return tid


def create_session(env_data: dict, session_id: str) -> Path:
    sess_path = env_data["project_root"] / "sessions" / "wip" / session_id / "session.json"
    if sess_path.exists():
        return sess_path
    run_cli(
        env_data,
        "session",
        "create",
        "--owner",
        "tester",
        "--session-id",
        session_id,
        "--no-worktree",
        "--repo-root",
        str(env_data["root"]),
    )
    return sess_path


def write_session_age(env_data: dict, session_id: str, *, hours_old: float, tz_variant: str = "Z") -> None:
    """Stamp createdAt/lastActive to an older timestamp."""
    sess_path = create_session(env_data, session_id)
    data = json.loads(sess_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=hours_old)
    ts = _write_iso(past, tz_variant=tz_variant)
    data["meta"]["createdAt"] = ts
    data["meta"]["lastActive"] = ts
    data["meta"].pop("claimedAt", None)
    sess_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestSessionTimeout:
    def test_detects_expired_session_and_cleans_up(self, session_timeout_env: dict) -> None:
        sid = "s-expired-clean"
        tid = create_task(session_timeout_env, 950, "wave2", "timeout-clean")

        create_session(session_timeout_env, sid)
        run_cli(session_timeout_env, "task", "claim", tid, "--session", sid, "--repo-root", str(session_timeout_env["root"]))

        # Make session older than configured timeout to trigger cleanup.
        write_session_age(session_timeout_env, sid, hours_old=float(TIMEOUT_HOURS + 4))

        dry = run_cli(session_timeout_env, "session", "cleanup-expired", "--dry-run", "--json")
        dry_payload = json.loads(dry.stdout or "{}")
        assert sid in set(dry_payload.get("expired", []))

        cleaned = run_cli(session_timeout_env, "session", "cleanup-expired", "--json")
        cleaned_payload = json.loads(cleaned.stdout or "{}")
        assert sid in set(cleaned_payload.get("cleaned", []))

        # Task restored globally in its current state (wip).
        global_path = session_timeout_env["project_root"] / "tasks" / "wip" / f"{tid}.md"
        assert global_path.exists()

        # Session transitioned to semantic "closing" (mapped to done/ directory in tests).
        sess_done = session_timeout_env["project_root"] / "sessions" / "done" / sid / "session.json"
        assert sess_done.exists()
        data = json.loads(sess_done.read_text(encoding="utf-8"))
        assert "expiredAt" in (data.get("meta") or {})

    def test_claim_rejected_when_session_expired(self, session_timeout_env: dict) -> None:
        sid = "s-expired-claim"
        tid = create_task(session_timeout_env, 951, "wave2", "timeout-claim")

        write_session_age(session_timeout_env, sid, hours_old=float(TIMEOUT_HOURS + 8))
        res = run_cli(
            session_timeout_env,
            "task",
            "claim",
            tid,
            "--session",
            sid,
            "--repo-root",
            str(session_timeout_env["root"]),
            check=False,
        )
        assert res.returncode != 0
        assert "expired" in (res.stderr or "").lower()

    def test_timezone_parsing_z_and_offset(self, session_timeout_env: dict) -> None:
        sid_z = "s-timezone-z"
        sid_off = "s-timezone-off"

        # Slightly old but not expired.
        write_session_age(session_timeout_env, sid_z, hours_old=1.5, tz_variant="Z")
        write_session_age(session_timeout_env, sid_off, hours_old=2.0, tz_variant="+00:00")

        dry = run_cli(session_timeout_env, "session", "cleanup-expired", "--dry-run", "--json")
        payload = json.loads(dry.stdout or "{}")
        expired = set(payload.get("expired", []))
        assert sid_z not in expired
        assert sid_off not in expired

    def test_clock_skew_small_future_is_tolerated(self, session_timeout_env: dict) -> None:
        sid = "s-skew-future"
        sess_path = create_session(session_timeout_env, sid)
        data = json.loads(sess_path.read_text(encoding="utf-8"))

        future = datetime.now(timezone.utc) + timedelta(minutes=2)
        data["meta"]["lastActive"] = _write_iso(future, tz_variant="Z")
        sess_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        dry = run_cli(session_timeout_env, "session", "cleanup-expired", "--dry-run", "--json")
        payload = json.loads(dry.stdout or "{}")
        assert sid not in set(payload.get("expired", []))

    def test_concurrent_cleanup_is_idempotent(self, session_timeout_env: dict) -> None:
        sid = "s-concurrent-clean"
        tid = create_task(session_timeout_env, 952, "wave2", "concurrent")

        create_session(session_timeout_env, sid)
        run_cli(session_timeout_env, "task", "claim", tid, "--session", sid, "--repo-root", str(session_timeout_env["root"]))
        write_session_age(session_timeout_env, sid, hours_old=float(TIMEOUT_HOURS + 2))

        cmd = [sys.executable, "-m", "edison", "session", "cleanup-expired", "--json"]
        env = session_timeout_env["env"]
        p1 = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p2 = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out1, err1 = p1.communicate(timeout=60)
        out2, err2 = p2.communicate(timeout=60)

        assert 0 in {p1.returncode, p2.returncode}, f"p1={p1.returncode} err={err1}\np2={p2.returncode} err={err2}"

        global_path = session_timeout_env["project_root"] / "tasks" / "wip" / f"{tid}.md"
        assert global_path.exists()
        done_json = session_timeout_env["project_root"] / "sessions" / "done" / sid / "session.json"
        assert done_json.exists()
