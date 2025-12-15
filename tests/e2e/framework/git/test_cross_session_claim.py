"""Cross-session reclaim behavior for tasks/claim.

TDD: enforce --reclaim for cross-session moves and surface timeout warning.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path
from tests.helpers.paths import get_repo_root, get_core_root
from tests.e2e.base import E2ETestCase


class TestCrossSessionClaim(E2ETestCase):
    def setUp(self) -> None:
        # Call parent setUp to get standard E2E environment
        super().setUp()

        # Get repo root and scripts directory
        self.project_root = get_repo_root()
        self.scripts_dir = get_data_path("scripts")

        # Override owner for this test
        self.env.update({
            "AGENTS_OWNER": "claude-pid-1111",
        })

        # Add script paths for convenience
        self.session_cli = self.scripts_dir / "session"
        self.tasks_claim = self.scripts_dir / "tasks" / "claim"

        # Rename self.tmp to self.temp_root for compatibility with existing test code
        self.temp_root = self.tmp

    def run_cli(self, *argv: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = ["python3", *[str(a) for a in argv]]
        res = run_with_timeout(cmd, cwd=self.scripts_dir, env=self.env, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise AssertionError(
                f"Command failed ({res.returncode})\nCMD: {' '.join(cmd)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        return res

    def _seed_task(self, task_id: str) -> Path:
        content = textwrap.dedent(
            f"""
            # {task_id}
            - **Task ID:** {task_id}
            - **Priority Slot:** {task_id.split('-')[0]}
            - **Wave:** {task_id.split('-')[1]}
            - **Owner:** _unassigned_
            - **Status:** todo
            - **Created:** 2025-11-16
            - **Session Info:**
              - **Claimed At:** _unassigned_
              - **Last Active:** _unassigned_
              - **Continuation ID:** _none_
              - **Primary Model:** _unassigned_
            """
        ).strip() + "\n"
        dest = self.temp_root / ".project" / "tasks" / "todo" / f"{task_id}.md"
        dest.write_text(content)
        return dest

    def _path_in_session_tasks(self, session_id: str, task_id: str, status: str = "wip") -> Path:
        return self.temp_root / ".project" / "sessions" / "wip" / session_id / "tasks" / status / f"{task_id}.md"

    def test_cross_session_claim_requires_reclaim_flag(self) -> None:
        """Verify claiming from another session without --reclaim fails and task stays put."""
        session_a = "session-a"
        session_b = "session-b"
        # Create two sessions
        self.run_cli(self.session_cli, "new", "--owner", "tester-a", "--session-id", session_a)
        self.run_cli(self.session_cli, "new", "--owner", "tester-b", "--session-id", session_b)

        task_id = "910-wave1-cross-reclaim"
        self._seed_task(task_id)

        # Claim into session A
        self.run_cli(self.tasks_claim, task_id, "--session", session_a)
        a_path = self._path_in_session_tasks(session_a, task_id)
        self.assertTrue(a_path.exists(), f"Expected in session A: {a_path}")

        # Attempt to claim from session B without --reclaim → must fail
        res = self.run_cli(self.tasks_claim, task_id, "--session", session_b, check=False)
        self.assertNotEqual(res.returncode, 0, "Cross-session claim without --reclaim should fail")
        self.assertIn("Use --reclaim", res.stderr)
        # File should remain in session A
        self.assertTrue(a_path.exists(), "Task must remain in original session")

    def test_reclaim_respects_timeout(self) -> None:
        """Reclaim prints a warning including session age and manifest timeout hours when below threshold."""
        session_a = "session-a2"
        session_b = "session-b2"
        self.run_cli(self.session_cli, "new", "--owner", "tester-a2", "--session-id", session_a)
        self.run_cli(self.session_cli, "new", "--owner", "tester-b2", "--session-id", session_b)

        task_id = "911-wave1-timeout-reclaim"
        self._seed_task(task_id)
        self.run_cli(self.tasks_claim, task_id, "--session", session_a)

        res = self.run_cli(self.tasks_claim, task_id, "--session", session_b, "--reclaim", check=False)
        # Should proceed (non-zero allowed before fix; after fix it may succeed) but must include warning about timeout
        self.assertIn("timeout", res.stderr.lower())
        self.assertIn("session is only", res.stderr.lower())

    def test_reclaim_with_flag_succeeds(self) -> None:
        """--reclaim allows cross-session move and file relocates to the new session."""
        session_a = "session-a3"
        session_b = "session-b3"
        self.run_cli(self.session_cli, "new", "--owner", "tester-a3", "--session-id", session_a)
        self.run_cli(self.session_cli, "new", "--owner", "tester-b3", "--session-id", session_b)

        task_id = "912-wave1-reclaim-success"
        self._seed_task(task_id)
        self.run_cli(self.tasks_claim, task_id, "--session", session_a)
        b_path = self._path_in_session_tasks(session_b, task_id)
        self.assertFalse(b_path.exists(), "Not yet in session B")

        res = self.run_cli(self.tasks_claim, task_id, "--session", session_b, "--reclaim")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(b_path.exists(), "Task should move to session B after reclaim")


if __name__ == "__main__":
    unittest.main()
