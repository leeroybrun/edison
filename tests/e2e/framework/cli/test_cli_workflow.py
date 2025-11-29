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
from typing import Iterable, Optional, Generator

import pytest

from tests.helpers.paths import get_repo_root, get_core_root
from tests.e2e.base import create_project_structure, copy_templates, setup_base_environment

REPO_ROOT = get_repo_root()
CORE_ROOT = get_core_root()
SCRIPTS_DIR = CORE_ROOT / "scripts"
from edison.core import task  # type: ignore  # pylint: disable=wrong-import-position
from edison.core.utils.subprocess import run_with_timeout


@pytest.fixture
def cli_workflow_env(tmp_path: Path) -> Generator[dict, None, None]:
    """Set up isolated test environment for CLI workflow tests."""
    temp_root = tmp_path / "workflow-tests"
    temp_root.mkdir()

    # Use shared base setup functions
    create_project_structure(temp_root)
    copy_templates(temp_root)
    base_env = setup_base_environment(temp_root)

    # Remove AGENTS_PROJECT_ROOT from base_env since this test uses project_ROOT
    base_env.pop("AGENTS_PROJECT_ROOT", None)

    project_root = temp_root / ".project"
    env_data = {
        "repo_root": REPO_ROOT,
        "temp_root": temp_root,
        "project_root": project_root,
        "sessions_root": project_root / "sessions",
        "tasks_root": project_root / "tasks",
        "qa_root": project_root / "qa",
        "base_env": base_env,
        "session_script": SCRIPTS_DIR / "session",
        "tasks_status_script": SCRIPTS_DIR / "tasks" / "status",
        "tasks_claim_script": SCRIPTS_DIR / "tasks" / "claim",
        "tasks_list_script": SCRIPTS_DIR / "tasks" / "list",
        "qa_new_script": SCRIPTS_DIR / "qa" / "new",
    }

    yield env_data

    # Cleanup happens automatically with tmp_path


def run_cli(env: dict, command: Iterable[str | Path], extra_env: Optional[dict[str, str]] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run CLI command with environment."""
    cmd = [str(part) for part in command]
    env_vars = env["base_env"].copy()
    if extra_env:
        env_vars.update(extra_env)
    result = run_with_timeout(cmd, cwd=env["repo_root"], env=env_vars, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command {' '.join(cmd)} failed with code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def create_task_file(env: dict, task_id: str) -> Path:
    """Create a test task file."""
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

    path = env["tasks_root"] / "todo" / f"{task_id}.md"
    path.write_text(content)
    return path


class TestDefaultOwner:
    """Tests for default owner detection."""

    def test_uses_detected_process_name(self) -> None:
        def fake_finder() -> tuple[str, int]:
            return ("claude", 4321)

        owner = task.default_owner(process_finder=fake_finder)
        assert owner == "claude"

    def test_falls_back_to_env_or_user_when_detection_fails(self) -> None:
        def failing_finder() -> tuple[str, int]:
            raise RuntimeError("No process found")

        # Ensure we don't accidentally pick up the real env var if set during test
        old_env = os.environ.get("AGENTS_OWNER")
        if "AGENTS_OWNER" in os.environ:
            del os.environ["AGENTS_OWNER"]

        try:
            import getpass
            expected_user = getpass.getuser()
            owner = task.default_owner(process_finder=failing_finder)
            assert owner == expected_user
        finally:
            if old_env is not None:
                os.environ["AGENTS_OWNER"] = old_env

    def test_prefers_env_var_over_user_fallback(self) -> None:
        def failing_finder() -> tuple[str, int]:
            raise RuntimeError("No process found")

        old_env = os.environ.get("AGENTS_OWNER")
        os.environ["AGENTS_OWNER"] = "env-defined-owner"
        try:
            owner = task.default_owner(process_finder=failing_finder)
            assert owner == "env-defined-owner"
        finally:
            if old_env:
                os.environ["AGENTS_OWNER"] = old_env
            else:
                del os.environ["AGENTS_OWNER"]


class TestScriptWorkflow:
    """Tests for end-to-end script workflows."""

    def test_session_new_rejects_duplicate_pid(self, cli_workflow_env: dict) -> None:
        session_id = "claude-pid-777"
        env_vars = {"project_OWNER": session_id}
        run_cli(cli_workflow_env, [cli_workflow_env["session_script"], "new", "--session-id", session_id], extra_env=env_vars)
        session_file = cli_workflow_env["sessions_root"] / "wip" / f"{session_id}.json"
        assert session_file.exists(), "Session file should be created for the PID-based ID"

        duplicate = run_cli(cli_workflow_env, [cli_workflow_env["session_script"], "new", "--session-id", session_id], extra_env=env_vars, check=False)
        assert duplicate.returncode != 0, "Duplicate PID session must exit with failure"
        combined_output = f"{duplicate.stdout}\n{duplicate.stderr}"
        assert "Session 'claude-pid-777' already exists" in combined_output

    def test_end_to_end_task_and_qa_flow(self, cli_workflow_env: dict) -> None:
        session_id = "claude-pid-888"
        env_vars = {"project_OWNER": session_id}
        task_id = "150-wave1-demo"
        create_task_file(cli_workflow_env, task_id)

        run_cli(cli_workflow_env, [cli_workflow_env["session_script"], "new", "--session-id", session_id], extra_env=env_vars)
        session_wip = cli_workflow_env["sessions_root"] / "wip" / f"{session_id}.json"
        assert session_wip.exists()

        # Intake summary (no --session flags required after creation)
        run_cli(cli_workflow_env, [cli_workflow_env["session_script"], "status", session_id], extra_env=env_vars)

        # Move task to wip and claim it (auto session detection via owner env)
        run_cli(cli_workflow_env, [cli_workflow_env["tasks_status_script"], task_id, "--status", "wip"], extra_env=env_vars)
        run_cli(cli_workflow_env, [cli_workflow_env["tasks_claim_script"], task_id], extra_env=env_vars)

        scope = json.loads(session_wip.read_text())
        assert task_id in scope["tasks"]

        # Create QA brief without passing --session; ensure scope updated (session-scoped)
        run_cli(cli_workflow_env, [cli_workflow_env["qa_new_script"], task_id], extra_env=env_vars)
        qa_file = cli_workflow_env["sessions_root"] / "wip" / session_id / "qa" / "waiting" / f"{task_id}-qa.md"
        assert qa_file.exists(), "QA brief should exist under session qa/waiting/"
        scope = json.loads(session_wip.read_text())
        assert f"{task_id}-qa" in scope["qa"]

        # tasks/list default excludes session items; use --session to see them
        list_output = run_cli(cli_workflow_env, [cli_workflow_env["tasks_list_script"], "--session", session_id, "--format", "json"], extra_env=env_vars).stdout
        records = { (rec["type"], rec["path"]): rec for rec in json.loads(list_output) }
        task_key = ("task", f".project/sessions/wip/{session_id}/tasks/wip/{task_id}.md")
        qa_key = ("qa", f".project/sessions/wip/{session_id}/qa/waiting/{task_id}-qa.md")
        assert task_key in records
        assert qa_key in records

        # Attempting to complete session early should fail
        incomplete = run_cli(cli_workflow_env, [cli_workflow_env["session_script"], "complete", session_id], extra_env=env_vars, check=False)
        assert incomplete.returncode != 0
        assert "cannot be completed" in (incomplete.stdout + incomplete.stderr)

        # Prepare round evidence so tasks/ready guard passes
        ev_round = cli_workflow_env["qa_root"] / "validation-evidence" / task_id / "round-1"
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
        run_cli(cli_workflow_env, [cli_workflow_env["tasks_status_script"], task_id, "--status", "done"], extra_env=env_vars)

        # Promote QA waiting->todo and begin validation
        run_cli(cli_workflow_env, [SCRIPTS_DIR / "qa" / "promote", "--task", task_id, "--to", "todo"], extra_env=env_vars)
        # Mark bundle approved and promote QA to wip → done
        summary_path = cli_workflow_env["qa_root"] / "validation-evidence" / task_id / "round-1" / "bundle-approved.json"
        summary_path.write_text("{\n  \"approved\": true\n}\n")
        run_cli(cli_workflow_env, [SCRIPTS_DIR / "qa" / "promote", "--task", task_id, "--to", "wip"], extra_env=env_vars)
        run_cli(cli_workflow_env, [SCRIPTS_DIR / "qa" / "promote", "--task", task_id, "--to", "done"], extra_env=env_vars)
        # Finally validate the task (requires QA done + bundle approved marker)
        run_cli(cli_workflow_env, [cli_workflow_env["tasks_status_script"], task_id, "--status", "validated"], extra_env=env_vars)

        # At this stage (before session complete), validated task/QA live under the session tree
        task_validated_session = cli_workflow_env["sessions_root"] / "wip" / session_id / "tasks" / "validated" / f"{task_id}.md"
        qa_done_session = cli_workflow_env["sessions_root"] / "wip" / session_id / "qa" / "done" / f"{task_id}-qa.md"
        assert task_validated_session.exists()
        assert qa_done_session.exists()

        # Final completion succeeds
        run_cli(cli_workflow_env, [cli_workflow_env["session_script"], "complete", session_id], extra_env=env_vars)
        # After completion, files are restored to global queues
        task_validated = cli_workflow_env["tasks_root"] / "validated" / f"{task_id}.md"
        qa_done = cli_workflow_env["qa_root"] / "done" / f"{task_id}-qa.md"
        assert task_validated.exists()
        assert qa_done.exists()
        session_validated = cli_workflow_env["sessions_root"] / "validated" / f"{session_id}.json"
        assert session_validated.exists(), "Session file should move to validated/"
        session_data = json.loads(session_validated.read_text())
        assert session_data["meta"]["status"] == "validated"
