"""Session timeout enforcement tests (WP-002).

TDD: verify detection, claim rejection, and cleanup behaviors.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import pytest

from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path
from tests.helpers.timeouts import wait_for_file
from tests.helpers.paths import get_repo_root, get_core_root
from tests.e2e.base import create_project_structure, copy_templates, setup_base_environment


REPO_ROOT = get_repo_root()
CORE_ROOT = get_core_root()
SCRIPTS_DIR = CORE_ROOT / "scripts"


def _write(ts: str) -> str:
    # Helpers to normalize ISO string with Z suffix
    return ts.replace("+00:00", "Z")


@pytest.fixture
def session_timeout_env(tmp_path: Path) -> Generator[dict, None, None]:
    """Set up isolated test environment for session timeout tests."""
    # Use shared base setup functions
    create_project_structure(tmp_path)
    copy_templates(tmp_path)
    env = setup_base_environment(tmp_path, owner="codex-pid-9999")

    env_data = {
        "tmp": tmp_path,
        "env": env,
        "session_cli": SCRIPTS_DIR / "session",
        "claim_cli": SCRIPTS_DIR / "tasks" / "claim",
        "detect_stale_cmd": [SCRIPTS_DIR / "session", "detect-stale"],
    }

    yield env_data


def run_cli(env_data: dict, *argv: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Execute CLI command with error handling."""
    cmd = ["python3", *[str(a) for a in argv]]
    res = run_with_timeout(cmd, cwd=SCRIPTS_DIR, env=env_data["env"], capture_output=True, text=True)
    if check and res.returncode != 0:
        raise AssertionError(
            f"Command failed ({res.returncode})\nCMD: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res


def seed_task(env_data: dict, task_id: str, status: str = "todo") -> Path:
    """Create a minimal task file for testing."""
    content = textwrap.dedent(
        f"""
        # {task_id}
        - **Task ID:** {task_id}
        - **Priority Slot:** {task_id.split('-')[0]}
        - **Wave:** {task_id.split('-')[1]}
        - **Owner:** _unassigned_
        - **Status:** {status}
        - **Created:** 2025-11-16
        - **Session Info:**
          - **Claimed At:** _unassigned_
          - **Last Active:** _unassigned_
          - **Continuation ID:** _none_
          - **Primary Model:** _unassigned_
        """
    ).strip() + "\n"
    dest = env_data["tmp"] / ".project" / "tasks" / status / f"{task_id}.md"
    dest.write_text(content)
    return dest


def write_session_age(env_data: dict, session_id: str, hours_old: float, tz_variant: str = "Z") -> None:
    """Ensure a session exists and stamp createdAt/lastActive accordingly.

    tz_variant: 'Z' or '+00:00'
    """
    # Create session via CLI if missing
    sess_path = env_data["tmp"] / ".project" / "sessions" / "wip" / f"{session_id}.json"
    if not sess_path.exists():
        run_cli(env_data, env_data["session_cli"], "new", "--owner", "tester", "--session-id", session_id)
    data = json.loads(sess_path.read_text())
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=hours_old)
    ts = past.isoformat(timespec="seconds")
    if tz_variant == "Z":
        ts = _write(ts)
    data["meta"]["createdAt"] = ts
    data["meta"]["lastActive"] = ts
    # Ensure no claimedAt to exercise fallback; later tests set it explicitly
    data["meta"].pop("claimedAt", None)
    sess_path.write_text(json.dumps(data, indent=2))


class TestSessionTimeout:
    """Session timeout enforcement tests."""

    def test_detects_expired_session_and_cleans_up(self, session_timeout_env: dict) -> None:
        """Expired session is detected and cleaned; tasks return to global queues."""
        sid = "s-expired-clean"
        task_id = "950-wave2-timeout-clean"
        seed_task(session_timeout_env, task_id)
        # Create session then claim into it
        run_cli(session_timeout_env, session_timeout_env["session_cli"], "new", "--owner", "tester", "--session-id", sid)
        run_cli(session_timeout_env, session_timeout_env["claim_cli"], task_id, "--session", sid)
        # Make session old (>8h default)
        write_session_age(session_timeout_env, sid, hours_old=12.0)

        # Run detector (expects script to exist; RED until implemented)
        res = run_cli(session_timeout_env, *session_timeout_env["detect_stale_cmd"], "--json")
        assert res.returncode == 0, res.stderr
        payload = json.loads(res.stdout or "{}")
        expired = payload.get("expiredSessions", [])
        cleaned = payload.get("cleanedSessions", [])
        assert sid in expired, f"Detector should report expired session: {payload}"
        assert sid in cleaned, f"Detector should report cleaned session: {payload}"

        # Verify task moved back to global wip
        global_path = session_timeout_env["tmp"] / ".project" / "tasks" / "wip" / f"{task_id}.md"
        assert global_path.exists(), f"Task should be restored globally: {global_path}"
        # Verify session moved to done and stamped
        sess_done = session_timeout_env["tmp"] / ".project" / "sessions" / "done" / f"{sid}.json"
        assert sess_done.exists(), f"Session JSON should move to done: {sess_done}"
        data = json.loads(sess_done.read_text())
        assert "expiredAt" in data.get("meta", {}), "Session should be stamped with expiredAt"

    def test_claim_rejected_when_session_expired(self, session_timeout_env: dict) -> None:
        """Claim must fail-closed if target session is expired."""
        sid = "s-expired-claim"
        task_id = "951-wave2-timeout-claim"
        seed_task(session_timeout_env, task_id)
        # Create old session before claim
        write_session_age(session_timeout_env, sid, hours_old=24.0)
        res = run_cli(session_timeout_env, session_timeout_env["claim_cli"], task_id, "--session", sid, check=False)
        assert res.returncode != 0, "Claim into expired session should fail"
        assert "expired" in res.stderr.lower()

    def test_timezone_parsing_z_and_offset(self, session_timeout_env: dict) -> None:
        """Detector handles both 'Z' and '+00:00' timestamps."""
        sid_z = "s-timezone-z"
        sid_off = "s-timezone-off"
        # Slightly old but not expired
        write_session_age(session_timeout_env, sid_z, hours_old=1.5, tz_variant="Z")
        write_session_age(session_timeout_env, sid_off, hours_old=2.0, tz_variant="+00:00")
        res = run_cli(session_timeout_env, *session_timeout_env["detect_stale_cmd"], "--json")
        payload = json.loads(res.stdout or "{}")
        expired = set(payload.get("expiredSessions", []))
        assert sid_z not in expired
        assert sid_off not in expired

    def test_clock_skew_small_future_is_tolerated(self, session_timeout_env: dict) -> None:
        """Small future skew in lastActive does not mark session expired."""
        sid = "s-skew-future"
        run_cli(session_timeout_env, session_timeout_env["session_cli"], "new", "--owner", "tester", "--session-id", sid)
        path = session_timeout_env["tmp"] / ".project" / "sessions" / "wip" / f"{sid}.json"
        data = json.loads(path.read_text())
        # lastActive 2 minutes in the future
        future = datetime.now(timezone.utc) + timedelta(minutes=2)
        data["meta"]["lastActive"] = _write(future.isoformat(timespec="seconds"))
        path.write_text(json.dumps(data, indent=2))
        res = run_cli(session_timeout_env, *session_timeout_env["detect_stale_cmd"], "--json")
        payload = json.loads(res.stdout or "{}")
        assert sid not in payload.get("expiredSessions", [])

    def test_concurrent_cleanup_is_idempotent(self, session_timeout_env: dict) -> None:
        """Running detector twice concurrently does not corrupt state and succeeds."""
        sid = "s-concurrent-clean"
        task_id = "952-wave2-concurrent"
        seed_task(session_timeout_env, task_id)
        run_cli(session_timeout_env, session_timeout_env["session_cli"], "new", "--owner", "tester", "--session-id", sid)
        run_cli(session_timeout_env, session_timeout_env["claim_cli"], task_id, "--session", sid)
        write_session_age(session_timeout_env, sid, hours_old=10.0)

        # Launch two detector processes
        p1 = run_cli(session_timeout_env, *session_timeout_env["detect_stale_cmd"], "--json", check=False)
        p2 = run_cli(session_timeout_env, *session_timeout_env["detect_stale_cmd"], "--json", check=False)
        assert 0 in {p1.returncode, p2.returncode}, "At least one detector run should succeed"
        # Verify final state
        global_path = session_timeout_env["tmp"] / ".project" / "tasks" / "wip" / f"{task_id}.md"
        assert global_path.exists()
        done_json = session_timeout_env["tmp"] / ".project" / "sessions" / "done" / f"{sid}.json"
        assert done_json.exists()
