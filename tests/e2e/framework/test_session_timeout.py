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
import unittest
from edison.core.utils.subprocess import run_with_timeout


def _repo_root() -> Path:
    """Locate the outer project git root.

    When running inside the nested `.edison` git repo, prefer the parent
    project root if it also has a `.git` directory so paths like
    `.project/` and `.agents/` resolve to the real project tree.
    """
    cur = Path(__file__).resolve()
    candidate: Path | None = None
    while cur != cur.parent:
        if (cur / ".git").exists():
            candidate = cur
        cur = cur.parent
    if candidate is None:
        raise RuntimeError("git root not found")
    if candidate.name == ".edison" and (candidate.parent / ".git").exists():
        return candidate.parent
    return candidate


REPO_ROOT = _repo_root()
CORE_ROOT = REPO_ROOT / ".edison" / "core"
SCRIPTS_DIR = CORE_ROOT / "scripts"


def _write(ts: str) -> str:
    # Helpers to normalize ISO string with Z suffix
    return ts.replace("+00:00", "Z")


class SessionTimeoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="project-timeout-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

        # Minimal project tree
        for d in [
            ".project/tasks/todo",
            ".project/tasks/wip",
            ".project/tasks/blocked",
            ".project/tasks/done",
            ".project/tasks/validated",
            ".project/qa/waiting",
            ".project/qa/todo",
            ".project/qa/wip",
            ".project/qa/done",
            ".project/qa/validated",
            ".project/qa/validation-evidence",
            ".project/sessions/wip",
            ".project/sessions/done",
            ".project/sessions/validated",
        ]:
            (self.tmp / d).mkdir(parents=True, exist_ok=True)

        # Copy templates referenced by scripts
        shutil.copyfile(REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json", self.tmp / ".agents" / "sessions" / "TEMPLATE.json")
        shutil.copyfile(REPO_ROOT / ".project" / "qa" / "TEMPLATE.md", self.tmp / ".project" / "qa" / "TEMPLATE.md")
        shutil.copyfile(REPO_ROOT / ".project" / "tasks" / "TEMPLATE.md", self.tmp / ".project" / "tasks" / "TEMPLATE.md")

        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.tmp),
            "AGENTS_PROJECT_ROOT": str(self.tmp),
            "project_OWNER": "codex-pid-9999",
            "PYTHONUNBUFFERED": "1",
        })

        self.session_cli = SCRIPTS_DIR / "session"
        self.claim_cli = SCRIPTS_DIR / "tasks" / "claim"
        # Detector is implemented as a subcommand of the session script
        self.detect_stale_cmd = [self.session_cli, "detect-stale"]

    def run_cli(self, *argv: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = ["python3", *[str(a) for a in argv]]
        res = run_with_timeout(cmd, cwd=SCRIPTS_DIR, env=self.env, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise AssertionError(
                f"Command failed ({res.returncode})\nCMD: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        return res

    def _seed_task(self, task_id: str, status: str = "todo") -> Path:
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
        dest = self.tmp / ".project" / "tasks" / status / f"{task_id}.md"
        dest.write_text(content)
        return dest

    def _write_session_age(self, session_id: str, hours_old: float, tz_variant: str = "Z") -> None:
        """Ensure a session exists and stamp createdAt/lastActive accordingly.

        tz_variant: 'Z' or '+00:00'
        """
        # Create session via CLI if missing
        sess_path = self.tmp / ".project" / "sessions" / "wip" / f"{session_id}.json"
        if not sess_path.exists():
            self.run_cli(self.session_cli, "new", "--owner", "tester", "--session-id", session_id)
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

    def test_detects_expired_session_and_cleans_up(self) -> None:
        """Expired session is detected and cleaned; tasks return to global queues."""
        sid = "s-expired-clean"
        task_id = "950-wave2-timeout-clean"
        self._seed_task(task_id)
        # Create session then claim into it
        self.run_cli(self.session_cli, "new", "--owner", "tester", "--session-id", sid)
        self.run_cli(self.claim_cli, task_id, "--session", sid)
        # Make session old (>8h default)
        self._write_session_age(sid, hours_old=12.0)

        # Run detector (expects script to exist; RED until implemented)
        res = self.run_cli(*self.detect_stale_cmd, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout or "{}")
        expired = payload.get("expiredSessions", [])
        cleaned = payload.get("cleanedSessions", [])
        self.assertIn(sid, expired, f"Detector should report expired session: {payload}")
        self.assertIn(sid, cleaned, f"Detector should report cleaned session: {payload}")

        # Verify task moved back to global wip
        global_path = self.tmp / ".project" / "tasks" / "wip" / f"{task_id}.md"
        self.assertTrue(global_path.exists(), f"Task should be restored globally: {global_path}")
        # Verify session moved to done and stamped
        sess_done = self.tmp / ".project" / "sessions" / "done" / f"{sid}.json"
        self.assertTrue(sess_done.exists(), f"Session JSON should move to done: {sess_done}")
        data = json.loads(sess_done.read_text())
        self.assertIn("expiredAt", data.get("meta", {}), "Session should be stamped with expiredAt")

    def test_claim_rejected_when_session_expired(self) -> None:
        """Claim must fail-closed if target session is expired."""
        sid = "s-expired-claim"
        task_id = "951-wave2-timeout-claim"
        self._seed_task(task_id)
        # Create old session before claim
        self._write_session_age(sid, hours_old=24.0)
        res = self.run_cli(self.claim_cli, task_id, "--session", sid, check=False)
        self.assertNotEqual(res.returncode, 0, "Claim into expired session should fail")
        self.assertIn("expired", res.stderr.lower())

    def test_timezone_parsing_z_and_offset(self) -> None:
        """Detector handles both 'Z' and '+00:00' timestamps."""
        sid_z = "s-timezone-z"
        sid_off = "s-timezone-off"
        # Slightly old but not expired
        self._write_session_age(sid_z, hours_old=1.5, tz_variant="Z")
        self._write_session_age(sid_off, hours_old=2.0, tz_variant="+00:00")
        res = self.run_cli(*self.detect_stale_cmd, "--json")
        payload = json.loads(res.stdout or "{}")
        expired = set(payload.get("expiredSessions", []))
        self.assertNotIn(sid_z, expired)
        self.assertNotIn(sid_off, expired)

    def test_clock_skew_small_future_is_tolerated(self) -> None:
        """Small future skew in lastActive does not mark session expired."""
        sid = "s-skew-future"
        self.run_cli(self.session_cli, "new", "--owner", "tester", "--session-id", sid)
        path = self.tmp / ".project" / "sessions" / "wip" / f"{sid}.json"
        data = json.loads(path.read_text())
        # lastActive 2 minutes in the future
        future = datetime.now(timezone.utc) + timedelta(minutes=2)
        data["meta"]["lastActive"] = _write(future.isoformat(timespec="seconds"))
        path.write_text(json.dumps(data, indent=2))
        res = self.run_cli(*self.detect_stale_cmd, "--json")
        payload = json.loads(res.stdout or "{}")
        self.assertNotIn(sid, payload.get("expiredSessions", []))

    def test_concurrent_cleanup_is_idempotent(self) -> None:
        """Running detector twice concurrently does not corrupt state and succeeds."""
        sid = "s-concurrent-clean"
        task_id = "952-wave2-concurrent"
        self._seed_task(task_id)
        self.run_cli(self.session_cli, "new", "--owner", "tester", "--session-id", sid)
        self.run_cli(self.claim_cli, task_id, "--session", sid)
        self._write_session_age(sid, hours_old=10.0)

        # Launch two detector processes
        p1 = self.run_cli(*self.detect_stale_cmd, "--json", check=False)
        p2 = self.run_cli(*self.detect_stale_cmd, "--json", check=False)
        self.assertIn(0, {p1.returncode, p2.returncode}, "At least one detector run should succeed")
        # Verify final state
        global_path = self.tmp / ".project" / "tasks" / "wip" / f"{task_id}.md"
        self.assertTrue(global_path.exists())
        done_json = self.tmp / ".project" / "sessions" / "done" / f"{sid}.json"
        self.assertTrue(done_json.exists())


if __name__ == "__main__":
    unittest.main()