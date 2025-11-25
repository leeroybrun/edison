"""Comprehensive tests for the project CLI scripts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Iterable, Optional
import unittest
from unittest import mock

def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root")


REPO_ROOT = get_repo_root()
CORE_ROOT = REPO_ROOT / ".edison" / "core"
SCRIPTS_DIR = CORE_ROOT / "scripts"
if str(CORE_ROOT) not in sys.path:

if str(SCRIPTS_DIR) not in sys.path:
from edison.core import task  # type: ignore  # pylint: disable=wrong-import-position
from edison.core.utils.subprocess import run_with_timeout


class DefaultOwnerTests(unittest.TestCase):
    def test_prefers_highest_llm_process_in_chain(self) -> None:
        chain = [(3210, "claude-helper"), (4321, "claude"), (1001, "zsh")]
        with mock.patch.object(task, "_calling_process_chain", return_value=chain):
            owner = task.default_owner()
        self.assertEqual(owner, "claude-pid-4321")

    def test_falls_back_to_first_non_llm_process(self) -> None:
        chain = [(2222, "cursor"), (1111, "wezterm")]
        with mock.patch.object(task, "_calling_process_chain", return_value=chain):
            owner = task.default_owner()
        self.assertEqual(owner, "cursor-pid-2222")

    def test_returns_none_when_no_calling_process_detected(self) -> None:
        with mock.patch.object(task, "_calling_process_chain", return_value=[]):
            owner = task.default_owner()
        self.assertIsNone(owner)


class ScriptWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = REPO_ROOT
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-script-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))
        self.project_root = self.temp_root / ".project"
        self.sessions_root = self.project_root / "sessions"
        self.tasks_root = self.project_root / "tasks"
        self.qa_root = self.project_root / "qa"
        self._init_project_layout()
        self.base_env = os.environ.copy()
        self.base_env.update(
            {
                "project_ROOT": str(self.temp_root),
                "PYTHONUNBUFFERED": "1",
            }
        )

        self.session_script = SCRIPTS_DIR / "session"
        self.tasks_status_script = SCRIPTS_DIR / "tasks" / "status"
        self.tasks_claim_script = SCRIPTS_DIR / "tasks" / "claim"
        self.tasks_list_script = SCRIPTS_DIR / "tasks" / "list"
        self.qa_new_script = SCRIPTS_DIR / "qa" / "new"

    def _init_project_layout(self) -> None:
        task_dirs = ["todo", "wip", "blocked", "done", "validated"]
        qa_dirs = ["waiting", "todo", "wip", "done", "validated", "validation-evidence"]
        session_dirs = ["wip", "done", "validated"]
        for directory in task_dirs:
            (self.tasks_root / directory).mkdir(parents=True, exist_ok=True)
        for directory in qa_dirs:
            (self.qa_root / directory).mkdir(parents=True, exist_ok=True)
        for directory in session_dirs:
            (self.sessions_root / directory).mkdir(parents=True, exist_ok=True)

        # Edison canonical session template location: .agents/sessions/TEMPLATE.json
        template_dest = self.temp_root / ".agents" / "sessions" / "TEMPLATE.json"
        template_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json",
            template_dest,
        )
        shutil.copyfile(
            REPO_ROOT / ".project" / "qa" / "TEMPLATE.md",
            self.qa_root / "TEMPLATE.md",
        )

    def _create_task_file(self, task_id: str) -> Path:
        content = textwrap.dedent(
            f"""
            # {task_id}

            - **Task ID:** {task_id}
            - **Priority Slot:** 150
            - **Wave:** wave1
            - **Owner:** _unassigned_
            - **Status:** todo
            - **Created:** 2025-11-13
            - **Session Info:**
              - **Claimed At:** _unassigned_
              - **Last Active:** _unassigned_
              - **Continuation ID:** _none_
              - **Primary Model:** _unassigned_

            ## Status Updates
            - 2025-11-13 00:00 UTC – Seed task created for tests.
            """
        ).strip() + "\n"

        path = self.tasks_root / "todo" / f"{task_id}.md"
        path.write_text(content)
        return path

    def run_cli(self, command: Iterable[str | Path], extra_env: Optional[dict[str, str]] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [str(part) for part in command]
        env = self.base_env.copy()
        if extra_env:
            env.update(extra_env)
        result = run_with_timeout(cmd, cwd=self.repo_root, env=env, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise AssertionError(
                f"Command {' '.join(cmd)} failed with code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return result

    def test_session_new_rejects_duplicate_pid(self) -> None:
        session_id = "claude-pid-777"
        env = {"project_OWNER": session_id}
        self.run_cli([self.session_script, "new", "--session-id", session_id], extra_env=env)
        session_file = self.sessions_root / "wip" / f"{session_id}.json"
        self.assertTrue(session_file.exists(), "Session file should be created for the PID-based ID")

        duplicate = self.run_cli([self.session_script, "new", "--session-id", session_id], extra_env=env, check=False)
        self.assertNotEqual(duplicate.returncode, 0, "Duplicate PID session must exit with failure")
        combined_output = f"{duplicate.stdout}\n{duplicate.stderr}"
        self.assertIn("Session 'claude-pid-777' already exists", combined_output)

    def test_end_to_end_task_and_qa_flow(self) -> None:
        session_id = "claude-pid-888"
        env = {"project_OWNER": session_id}
        task_id = "150-wave1-demo"
        self._create_task_file(task_id)

        self.run_cli([self.session_script, "new", "--session-id", session_id], extra_env=env)
        session_wip = self.sessions_root / "wip" / f"{session_id}.json"
        self.assertTrue(session_wip.exists())

        # Intake summary (no --session flags required after creation)
        self.run_cli([self.session_script, "status", session_id], extra_env=env)

        # Move task to wip and claim it (auto session detection via owner env)
        self.run_cli([self.tasks_status_script, task_id, "--status", "wip"], extra_env=env)
        self.run_cli([self.tasks_claim_script, task_id], extra_env=env)

        scope = json.loads(session_wip.read_text())
        self.assertIn(task_id, scope["tasks"])

        # Create QA brief without passing --session; ensure scope updated (session-scoped)
        self.run_cli([self.qa_new_script, task_id], extra_env=env)
        qa_file = self.sessions_root / "wip" / session_id / "qa" / "waiting" / f"{task_id}-qa.md"
        self.assertTrue(qa_file.exists(), "QA brief should exist under session qa/waiting/")
        scope = json.loads(session_wip.read_text())
        self.assertIn(f"{task_id}-qa", scope["qa"])

        # tasks/list default excludes session items; use --session to see them
        list_output = self.run_cli([self.tasks_list_script, "--session", session_id, "--format", "json"], extra_env=env).stdout
        records = { (rec["type"], rec["path"]): rec for rec in json.loads(list_output) }
        task_key = ("task", f".project/sessions/wip/{session_id}/tasks/wip/{task_id}.md")
        qa_key = ("qa", f".project/sessions/wip/{session_id}/qa/waiting/{task_id}-qa.md")
        self.assertIn(task_key, records)
        self.assertIn(qa_key, records)

        # Attempting to complete session early should fail
        incomplete = self.run_cli([self.session_script, "complete", session_id], extra_env=env, check=False)
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertIn("cannot be completed", incomplete.stdout + incomplete.stderr)

        # Prepare round evidence so tasks/ready guard passes
        ev_round = self.qa_root / "validation-evidence" / task_id / "round-1"
        ev_round.mkdir(parents=True, exist_ok=True)
        for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
            (ev_round / name).write_text("ok\n")
        # Minimal implementation report required now
        (ev_round / "implementation-report.json").write_text(
            (
                "{"
                "\"taskId\":\"%s\",\n" % task_id +
                "\"round\":1,\n"
                "\"implementationApproach\":\"orchestrator-direct\",\n"
                "\"primaryModel\":\"claude\",\n"
                "\"completionStatus\":\"complete\",\n"
                "\"followUpTasks\":[],\n"
                "\"notesForValidator\":\"ok\",\n"
                "\"tracking\":{\"startedAt\":\"t\",\"processId\":123,\"completedAt\":\"t2\"}"
                + "}"
            )
        )

        # Move task to done (guard will run tasks/ready)
        self.run_cli([self.tasks_status_script, task_id, "--status", "done"], extra_env=env)

        # Promote QA waiting->todo and begin validation
        self.run_cli([SCRIPTS_DIR / "qa" / "promote", "--task", task_id, "--to", "todo"], extra_env=env)
        # Mark bundle approved and promote QA to wip → done
        summary_path = self.qa_root / "validation-evidence" / task_id / "round-1" / "bundle-approved.json"
        summary_path.write_text("{\n  \"approved\": true\n}\n")
        self.run_cli([SCRIPTS_DIR / "qa" / "promote", "--task", task_id, "--to", "wip"], extra_env=env)
        self.run_cli([SCRIPTS_DIR / "qa" / "promote", "--task", task_id, "--to", "done"], extra_env=env)
        # Finally validate the task (requires QA done + bundle approved marker)
        self.run_cli([self.tasks_status_script, task_id, "--status", "validated"], extra_env=env)

        # At this stage (before session complete), validated task/QA live under the session tree
        task_validated_session = self.sessions_root / "wip" / session_id / "tasks" / "validated" / f"{task_id}.md"
        qa_done_session = self.sessions_root / "wip" / session_id / "qa" / "done" / f"{task_id}-qa.md"
        self.assertTrue(task_validated_session.exists())
        self.assertTrue(qa_done_session.exists())

        # Final completion succeeds
        self.run_cli([self.session_script, "complete", session_id], extra_env=env)
        # After completion, files are restored to global queues
        task_validated = self.tasks_root / "validated" / f"{task_id}.md"
        qa_done = self.qa_root / "done" / f"{task_id}-qa.md"
        self.assertTrue(task_validated.exists())
        self.assertTrue(qa_done.exists())
        session_validated = self.sessions_root / "validated" / f"{session_id}.json"
        self.assertTrue(session_validated.exists(), "Session file should move to validated/")
        session_data = json.loads(session_validated.read_text())
        self.assertEqual(session_data["meta"]["status"], "validated")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()