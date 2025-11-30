"""Contract tests for tasks/status stdout vs stderr behavior.

Focus: --json mode must emit pure JSON on stdout with all diagnostics routed
to stderr, including during the merge-archival hook.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()
SCRIPTS_DIR = REPO_ROOT / "scripts"


class TestStatusJsonPurity(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = REPO_ROOT
        self.tmp = Path(tempfile.mkdtemp(prefix="project-status-json-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

        # Minimal project project layout under temp root
        (self.tmp / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
        (self.tmp / ".project" / "qa" / "done").mkdir(parents=True, exist_ok=True)
        (self.tmp / ".project" / "sessions" / "active").mkdir(parents=True, exist_ok=True)
        (self.tmp / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Initialize git repo for task operations
        run_with_timeout(["git", "init"], cwd=self.tmp, capture_output=True, check=True)
        run_with_timeout(["git", "config", "user.email", "you@example.com"], cwd=self.tmp, capture_output=True, check=True)
        run_with_timeout(["git", "config", "user.name", "Your Name"], cwd=self.tmp, capture_output=True, check=True)

        self.env = os.environ.copy()
        self.env.update({
            "project_ROOT": str(self.tmp),
            "PYTHONUNBUFFERED": "1",
        })

        self.status_script = SCRIPTS_DIR / "tasks" / "status"

        # Skip if script doesn't exist (contract tests for external project scripts)
        if not self.status_script.exists():
            self.skipTest(f"Script not found: {self.status_script}. These are contract tests for Edison-enabled projects.")

    def _run(self, args: list[str|Path]) -> subprocess.CompletedProcess[str]:
        return run_with_timeout([str(a) for a in ([self.status_script] + args)], cwd=self.repo_root, env=self.env, capture_output=True, text=True)

    def _write(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_status_json_pure_during_archival(self) -> None:
        """--json output remains pure JSON while archival logs go to stderr.

        Notes:
        - Use a unique session/task id per run to avoid collisions with any
          previously archived worktrees that may linger between local test runs.
        - Only stdout should contain JSON; archival diagnostics must appear on
          stderr. The test doesn’t require an active auto-detected session.
        """
        import uuid
        sid = f"t{uuid.uuid4().hex[:10]}"
        task_id = f"999-merge-{sid}"

        # Create merge task in tasks/done with required Status line
        task_md = "\n".join([
            f"# {task_id}",
            "",
            "- **Status:** done",
            "",
            "Some content",
            "",
        ]) + "\n"
        self._write(self.tmp / ".project" / "tasks" / "done" / f"{task_id}.md", task_md)

        # Pair QA brief in qa/done
        qa_md = "\n".join([
            f"# {task_id}-qa",
            "- **Status:** done",
            "",
            "Bundle Approved: true",
        ]) + "\n"
        self._write(self.tmp / ".project" / "qa" / "done" / f"{task_id}-qa.md", qa_md)

        # Evidence bundle approved
        ev = self.tmp / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        ev.mkdir(parents=True, exist_ok=True)
        (ev / "bundle-approved.json").write_text(json.dumps({"approved": True}))

        # Session with git metadata and worktree path to trigger archival hook
        worktree = self.tmp / "_worktree" / sid
        worktree.mkdir(parents=True, exist_ok=True)
        session = {
            "meta": {"sessionId": sid, "owner": "tester", "mode": "auto", "status": "active", "createdAt": "", "lastActive": ""},
            "git": {"worktreePath": str(worktree), "archived": False, "databaseUrl": "sqlite:///tmp.db"},
            "tasks": {},
            "qa": {},
            "activityLog": [{"timestamp": "", "message": "init"}],
        }
        sess_path = self.tmp / ".project" / "sessions" / "active" / f"{sid}.json"
        self._write(sess_path, json.dumps(session))

        # Act: promote task to validated with --json
        res = self._run([task_id, "--status", "validated", "--json"])
        self.assertEqual(res.returncode, 0, f"status failed: {res.stderr}\nSTDOUT:{res.stdout}")

        # Assert stdout is pure JSON (no emojis/text logs)
        out = res.stdout.strip()
        json_obj = json.loads(out)  # must parse
        self.assertIsInstance(json_obj, dict)
        self.assertEqual(json_obj.get("to"), "validated")

        # Logs must go to stderr (archival + db drop)
        self.assertIn("Worktree archived", res.stderr)
        self.assertIn("Session database dropped", res.stderr)

    def test_status_without_json_can_use_human_output(self) -> None:
        """Non-JSON mode should produce human-oriented output (on stderr)."""
        task_id = "stdout-vs-stderr-1"
        task_md = "\n".join([
            f"# {task_id}",
            "- **Status:** wip",
            "",
        ]) + "\n"
        p = self._write(self.tmp / ".project" / "tasks" / "wip" / f"{task_id}.md", task_md)

        res = self._run(["--path", p])
        self.assertEqual(res.returncode, 0)
        # In non-JSON mode, prefer logs on stderr; stdout should be empty or minimal
        self.assertTrue(res.stderr.strip(), "expected human-readable output on stderr")

    def test_all_log_messages_to_stderr(self) -> None:
        """With --json, stdout is always parseable JSON and logs are in stderr."""
        task_id = "json-only-1"
        task_md = "\n".join([
            f"# {task_id}",
            "- **Status:** wip",
            "",
        ]) + "\n"
        self._write(self.tmp / ".project" / "tasks" / "wip" / f"{task_id}.md", task_md)

        res = self._run([task_id, "--json"])
        self.assertEqual(res.returncode, 0)
        # stdout must be valid JSON
        json.loads(res.stdout or "{}")
        # any non-empty logs show up in stderr, not stdout
        self.assertNotIn("📦", res.stdout)
        self.assertNotIn("✅", res.stdout)

    def test_json_parseable_at_all_times(self) -> None:
        """--json output should always be parseable JSON (no stray logs)."""
        task_id = "json-parseable-1"
        task_md = "\n".join([
            f"# {task_id}",
            "- **Status:** blocked",
            "",
        ]) + "\n"
        self._write(self.tmp / ".project" / "tasks" / "blocked" / f"{task_id}.md", task_md)
        res = self._run([task_id, "--json"])
        self.assertEqual(res.returncode, 0)
        json.loads(res.stdout)


if __name__ == "__main__":
    unittest.main()