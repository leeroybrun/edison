from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from edison.core.session.config import SessionConfig
from edison.core.utils.subprocess import run_with_timeout

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / ".edison" / "core"


class SessionRollbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = REPO_ROOT
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-session-rollback-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Minimal project layout
        pr = self.temp_root / ".project"
        for d in ["todo", "wip", "blocked", "done", "validated"]:
            (pr / "tasks" / d).mkdir(parents=True, exist_ok=True)
        for d in ["waiting", "todo", "wip", "done", "validated", "validation-evidence"]:
            (pr / "qa" / d).mkdir(parents=True, exist_ok=True)
        for d in ["active", "closing", "validated"]:
            (pr / "sessions" / d).mkdir(parents=True, exist_ok=True)

        # Required templates for session creation
        (self.temp_root / ".agents" / "sessions").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            self.repo_root / ".agents" / "sessions" / "TEMPLATE.json",
            self.temp_root / ".agents" / "sessions" / "TEMPLATE.json",
        )
        # QA template used by various helpers
        (self.temp_root / ".project" / "qa").mkdir(parents=True, exist_ok=True)
        if (self.repo_root / ".project" / "qa" / "TEMPLATE.md").exists():
            shutil.copyfile(
                self.repo_root / ".project" / "qa" / "TEMPLATE.md",
                self.temp_root / ".project" / "qa" / "TEMPLATE.md",
            )

        self.base_env = os.environ.copy()
        self.base_env.update({
            "project_ROOT": str(self.temp_root),
            "AGENTS_PROJECT_ROOT": str(self.temp_root),
            "PYTHONUNBUFFERED": "1",
        })

        self.session_cli = SCRIPTS_DIR / "scripts" / "session"

        # Reload config-driven modules so cached paths use temp root
        import importlib
        import edison.core.paths.resolver as resolver  # type: ignore
        resolver._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
        import edison.core.session.store as session_store  # type: ignore
        import edison.core.session.manager as session_manager  # type: ignore
        import edison.core.session.recovery as session_recovery  # type: ignore
        import edison.core.session.transaction as session_transaction  # type: ignore
        import edison.core.task as _task  # type: ignore
        import importlib
        importlib.reload(session_store)
        importlib.reload(session_manager)
        importlib.reload(session_recovery)
        importlib.reload(session_transaction)
        importlib.reload(_task)

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [str(self.session_cli), *args]
        res = run_with_timeout(cmd, cwd=self.repo_root, env=self.base_env, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise AssertionError(
                f"Command {' '.join(cmd)} failed ({res.returncode})\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        return res

    def _create_session(self, sid: str) -> None:
        self._run("new", "--session-id", sid, "--owner", "tester", "--mode", "start", check=True)

    def _session_dir(self, sid: str) -> Path:
        cfg = SessionConfig()
        init_state = cfg.get_initial_session_state()
        dir_name = cfg.get_session_states().get(init_state, init_state)
        return self.temp_root / ".project" / "sessions" / dir_name / sid

    def _seed_session_tasks(self, sid: str, count: int) -> list[str]:
        session_dir = self._session_dir(sid)
        (session_dir / "tasks" / "done").mkdir(parents=True, exist_ok=True)
        sess_json = session_dir / "session.json"
        data = json.loads(sess_json.read_text())
        data.setdefault("tasks", {})
        ids: list[str] = []
        for i in range(1, count + 1):
            task_id = f"t-{i:02d}"
            ids.append(task_id)
            path = session_dir / "tasks" / "done" / f"{task_id}.md"
            path.write_text("# {0}\n- **Owner:** tester\n- **Status:** done\n".format(task_id))
            data["tasks"][task_id] = {
                "recordId": task_id,
                "status": "done",
                "owner": "tester",
                "parentId": "p-1",
                "childIds": [],
            }
        sess_json.write_text(json.dumps(data, indent=2) + "\n")
        return ids

    def test_partial_restore_triggers_rollback(self) -> None:
        """Verify partial restore failure triggers full rollback"""
        sid = "rollback-partial"
        self._create_session(sid)
        ids = self._seed_session_tasks(sid, 5)

        # Lock destination for the 3rd record to force failure mid-restore
        lock = self.temp_root / ".project" / "tasks" / "done" / f"{ids[2]}.md.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("lock")

        result = self._run("complete", sid, check=False)
        self.assertNotEqual(result.returncode, 0, msg=f"expected non-zero on failure, got: {result.stderr}")
        self.assertIn("Rolled back", result.stderr)

        session_dir = self._session_dir(sid)
        # All records must remain in session scope; none in global
        for tid in ids:
            self.assertTrue((session_dir / "tasks" / "done" / f"{tid}.md").exists(), f"missing in session: {tid}")
            self.assertFalse((self.temp_root / ".project" / "tasks" / "done" / f"{tid}.md").exists(), f"unexpected in global: {tid}")

        # Journal should include rollback entries
        tx_dir = self.temp_root / ".project" / "sessions" / "_tx" / sid
        self.assertTrue(tx_dir.exists(), "transaction journal directory missing")
        # At least one rollback journal file present
        rollback_seen = False
        for jf in tx_dir.glob("*.json"):
            try:
                j = json.loads(jf.read_text())
                if str(j.get("domain", "")).startswith("rollback-"):
                    rollback_seen = True
                    break
            except Exception:
                continue
        self.assertTrue(rollback_seen, "no rollback journal entries found")

    def test_successful_restore_no_rollback(self) -> None:
        """Verify successful restore doesn't trigger rollback"""
        sid = "rollback-success"
        self._create_session(sid)
        ids = self._seed_session_tasks(sid, 3)

        result = self._run("complete", sid, check=True)
        self.assertEqual(result.returncode, 0)

        # Global has all, session has none
        for tid in ids:
            self.assertTrue((self.temp_root / ".project" / "tasks" / "done" / f"{tid}.md").exists())
            self.assertFalse((self.temp_root / ".project" / "sessions" / "active" / sid / "tasks" / "done" / f"{tid}.md").exists())

    def test_rollback_preserves_session_integrity(self) -> None:
        """Verify rollback doesn't corrupt session state and can complete later"""
        sid = "rollback-retry"
        self._create_session(sid)
        ids = self._seed_session_tasks(sid, 4)

        # Force failure on 2nd record
        lock = self.temp_root / ".project" / "tasks" / "done" / f"{ids[1]}.md.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("lock")

        res1 = self._run("complete", sid, check=False)
        self.assertNotEqual(res1.returncode, 0)

        # Metadata should still be in session and not validated
        sess_json = self._session_dir(sid) / "session.json"
        payload = json.loads(sess_json.read_text())
        self.assertNotEqual(payload.get("state"), "validated")
        self.assertNotEqual(payload.get("meta", {}).get("status"), "validated")

        # Remove lock and try again
        lock.unlink(missing_ok=True)  # type: ignore[arg-type]
        res2 = self._run("complete", sid, check=True)
        self.assertEqual(res2.returncode, 0)

        for tid in ids:
            self.assertTrue((self.temp_root / ".project" / "tasks" / "done" / f"{tid}.md").exists())
            self.assertFalse((self._session_dir(sid) / "tasks" / "done" / f"{tid}.md").exists())


if __name__ == "__main__":
    unittest.main()