from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path
from tests.config import get_task_states, get_qa_states, get_session_states
from tests.helpers.paths import get_repo_root

REPO_ROOT = get_repo_root()
SESSION_CLI = REPO_ROOT / ".agents" / "scripts" / "session"
TASKS_READY_CLI = REPO_ROOT / ".agents" / "scripts" / "tasks" / "ready"


@unittest.skipIf(not (SESSION_CLI.exists() and TASKS_READY_CLI.exists()), "session/tasks CLI not present in this repo snapshot")
class TestImplementationReportGuard(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-delegation-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))

        # Load state directories from config (NO hardcoded values)
        task_states = get_task_states()
        qa_states = get_qa_states()
        session_states = get_session_states()

        # Create task directories
        for state in task_states:
            (self.temp_root / ".project" / "tasks" / state).mkdir(parents=True, exist_ok=True)

        # Create QA directories
        for state in qa_states:
            (self.temp_root / ".project" / "qa" / state).mkdir(parents=True, exist_ok=True)
        (self.temp_root / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Create session directories
        for state in session_states:
            (self.temp_root / ".project" / "sessions" / state).mkdir(parents=True, exist_ok=True)
        # Templates
        (self.temp_root / ".agents" / "sessions").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(get_data_path("templates", "session.template.json"), self.temp_root / ".agents" / "sessions" / "TEMPLATE.json")
        shutil.copyfile(REPO_ROOT / ".project" / "qa" / "TEMPLATE.md", self.temp_root / ".project" / "qa" / "TEMPLATE.md")
        self.env = os.environ.copy()
        self.env.update({"AGENTS_PROJECT_ROOT": str(self.temp_root), "AGENTS_OWNER": "claude-pid-111"})
        self.session = SESSION_CLI
        self.tasks_ready = TASKS_READY_CLI
        # Create session with deterministic ID matching AGENTS_OWNER
        run_with_timeout([str(self.session), "new", "--session-id", self.env["AGENTS_OWNER"]], cwd=REPO_ROOT, env=self.env, check=True, text=True, capture_output=True)

    def test_implementation_report_required_for_all_tasks(self) -> None:
        task_id = "300-wave1-demo"
        task_path = self.temp_root / ".project" / "tasks" / "wip" / f"{task_id}.md"
        task_path.write_text(
            """
            # 300-wave1-demo
            - **Task ID:** 300-wave1-demo
            - **Owner:** claude
            - **Status:** wip
            - **Session Info:**
              - **Claimed At:** 2025-11-14
              - **Last Active:** 2025-11-14
              - **Continuation ID:** _none_
              - **Primary Model:** claude
              - **Delegated:** false
            """
        )
        # Create QA brief in waiting (tasks/ready requires QA present)
        qa_waiting = self.temp_root / ".project" / "qa" / "waiting" / f"{task_id}-qa.md"
        qa_waiting.write_text("# qa\n- **Status:** waiting\n")
        # Evidence dir
        round_dir = self.temp_root / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
            (round_dir / name).write_text("ok\n")
        # tasks/ready should fail because implementation-report.md is missing
        res = run_with_timeout([str(self.tasks_ready), task_id], cwd=REPO_ROOT, env=self.env, text=True, capture_output=True)
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Implementation report", (res.stdout + res.stderr))
        # Provide a minimal valid implementation report
        (round_dir / "implementation-report.md").write_text(
            """---
taskId: "300-wave1-demo"
round: 1
implementationApproach: "orchestrator-direct"
primaryModel: "claude"
completionStatus: "complete"
followUpTasks: []
notesForValidator: "ok"
tracking:
  processId: 123
  startedAt: "2025-12-15T00:00:00Z"
  completedAt: "2025-12-15T00:00:01Z"
---

# Implementation Report
ok
""",
            encoding="utf-8",
        )
        res = run_with_timeout([str(self.tasks_ready), task_id], cwd=REPO_ROOT, env=self.env, text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()
