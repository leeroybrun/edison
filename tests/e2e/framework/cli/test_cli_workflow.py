"""Comprehensive tests for the project CLI scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Generator

import pytest

from tests.helpers.paths import get_repo_root
from tests.e2e.base import create_project_structure, copy_templates, setup_base_environment
from tests.config import get_default_value
from edison.core.utils.text import format_frontmatter

REPO_ROOT = get_repo_root()
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

    project_root = temp_root / ".project"
    env_data = {
        "repo_root": REPO_ROOT,
        "temp_root": temp_root,
        "project_root": project_root,
        "sessions_root": project_root / "sessions",
        "tasks_root": project_root / "tasks",
        "qa_root": project_root / "qa",
        "base_env": base_env,
    }

    yield env_data

    # Cleanup happens automatically with tmp_path


def run_cli(env: dict, command: Iterable[str | Path], extra_env: Optional[dict[str, str]] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run `python -m edison` command with environment."""
    cmd = [sys.executable, "-m", "edison"] + [str(part) for part in command]
    env_vars = env["base_env"].copy()
    if extra_env:
        env_vars.update(extra_env)
    # Ensure the subprocess can import the in-repo `edison` package.
    src_root = Path(env["repo_root"]) / "src"
    existing_py_path = env_vars.get("PYTHONPATH", "")
    py_parts = [str(src_root)]
    if existing_py_path:
        py_parts.append(existing_py_path)
    env_vars["PYTHONPATH"] = os.pathsep.join(py_parts)
    result = run_with_timeout(cmd, cwd=env["repo_root"], env=env_vars, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command {' '.join(cmd)} failed with code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


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
        env_vars = {"AGENTS_OWNER": "tester"}
        run_cli(
            cli_workflow_env,
            ["session", "create", "--owner", "tester", "--session-id", session_id, "--mode", "start", "--no-worktree"],
            extra_env=env_vars,
        )
        session_file = cli_workflow_env["sessions_root"] / "wip" / session_id / "session.json"
        assert session_file.exists(), "Session file should be created for the PID-based ID"

        duplicate = run_cli(
            cli_workflow_env,
            ["session", "create", "--owner", "tester", "--session-id", session_id, "--mode", "start", "--no-worktree"],
            extra_env=env_vars,
            check=False,
        )
        assert duplicate.returncode != 0, "Duplicate PID session must exit with failure"
        combined_output = f"{duplicate.stdout}\n{duplicate.stderr}"
        assert "already exists" in combined_output.lower()
        assert session_id in combined_output

    def test_end_to_end_task_and_qa_flow(self, cli_workflow_env: dict) -> None:
        session_id = "claude-pid-888"
        task_id = "150-wave1-demo"
        env_vars = {"AGENTS_OWNER": "tester"}

        run_cli(
            cli_workflow_env,
            ["session", "create", "--owner", "tester", "--session-id", session_id, "--mode", "start", "--no-worktree"],
            extra_env=env_vars,
        )
        session_wip = cli_workflow_env["sessions_root"] / "wip" / session_id / "session.json"
        assert session_wip.exists()

        run_cli(cli_workflow_env, ["session", "status", session_id], extra_env=env_vars)

        # Create task and claim it into session (session-scoped)
        run_cli(cli_workflow_env, ["task", "new", "--id", "150", "--wave", "wave1", "--slug", "demo"], extra_env=env_vars)
        run_cli(cli_workflow_env, ["task", "claim", task_id, "--session", session_id], extra_env=env_vars)

        task_wip = cli_workflow_env["sessions_root"] / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md"
        assert task_wip.exists()

        # Claiming a task moves its QA record into the session scope.
        qa_file = cli_workflow_env["sessions_root"] / "wip" / session_id / "qa" / "waiting" / f"{task_id}-qa.md"
        assert qa_file.exists(), "QA brief should exist under session qa/waiting/"

        task_list_output = run_cli(cli_workflow_env, ["task", "list", "--session", session_id, "--json"], extra_env=env_vars).stdout
        task_records = {rec["path"]: rec for rec in json.loads(task_list_output)}
        assert f".project/sessions/wip/{session_id}/tasks/wip/{task_id}.md" in task_records

        qa_list_output = run_cli(
            cli_workflow_env,
            ["task", "list", "--type", "qa", "--session", session_id, "--json"],
            extra_env=env_vars,
        ).stdout
        qa_records = {rec["path"]: rec for rec in json.loads(qa_list_output)}
        assert f".project/sessions/wip/{session_id}/qa/waiting/{task_id}-qa.md" in qa_records

        # Attempting to complete session early should fail
        incomplete = run_cli(cli_workflow_env, ["session", "complete", session_id], extra_env=env_vars, check=False)
        assert incomplete.returncode != 0
        assert "verification" in (incomplete.stdout + incomplete.stderr).lower()

        # Prepare round evidence so guards pass
        ev_round = cli_workflow_env["qa_root"] / "validation-reports" / task_id / "round-1"
        ev_round.mkdir(parents=True, exist_ok=True)
        for name in get_default_value("qa", "evidence_files"):
            (ev_round / name).write_text("ok\n")
        (ev_round / "implementation-report.md").write_text(
            format_frontmatter(
                {
                    "taskId": task_id,
                    "round": 1,
                    "implementationApproach": "orchestrator-direct",
                    "primaryModel": "claude",
                    "completionStatus": "complete",
                    "followUpTasks": [],
                    "notesForValidator": "ok",
                    "tracking": {"startedAt": "t", "processId": 123, "completedAt": "t2"},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        # Move task to done and run QA workflow
        run_cli(cli_workflow_env, ["task", "status", task_id, "--status", "done", "--force"], extra_env=env_vars)
        run_cli(cli_workflow_env, ["qa", "promote", task_id, "--status", "todo", "--session", session_id], extra_env=env_vars)
        run_cli(cli_workflow_env, ["qa", "promote", task_id, "--status", "wip", "--session", session_id], extra_env=env_vars)

        # Provide minimal blocking validator approvals (config-driven roster)
        for vid, model in (("global-codex", "codex"), ("global-claude", "claude"), ("security", "codex"), ("performance", "codex")):
            report = {
                "taskId": task_id,
                "round": 1,
                "validatorId": vid,
                "model": model,
                "verdict": "approve",
                "findings": [],
                "strengths": [],
                "evidenceReviewed": [],
                "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:05:00Z"},
            }
            (ev_round / f"validator-{vid}-report.md").write_text(format_frontmatter(report) + "\n", encoding="utf-8")

        # Generate bundle-summary.md from existing evidence (no validator execution)
        run_cli(cli_workflow_env, ["qa", "validate", task_id, "--session", session_id, "--check-only"], extra_env=env_vars)

        # Promote QA wip → done and mark task validated
        run_cli(cli_workflow_env, ["qa", "promote", task_id, "--status", "done", "--session", session_id], extra_env=env_vars)
        run_cli(cli_workflow_env, ["task", "status", task_id, "--status", "validated"], extra_env=env_vars)

        # At this stage (before session complete), validated task/QA live under the session tree
        task_validated_session = cli_workflow_env["sessions_root"] / "wip" / session_id / "tasks" / "validated" / f"{task_id}.md"
        qa_done_session = cli_workflow_env["sessions_root"] / "wip" / session_id / "qa" / "done" / f"{task_id}-qa.md"
        assert task_validated_session.exists()
        assert qa_done_session.exists()

        # Session completion requires session-close command evidence. E2E tests
        # provide deterministic CI commands (see tests/e2e/base.py), so capture
        # those artifacts before completing.
        run_cli(cli_workflow_env, ["evidence", "init", task_id], extra_env=env_vars)
        run_cli(cli_workflow_env, ["evidence", "capture", task_id, "--session-close"], extra_env=env_vars)

        # Final completion succeeds
        run_cli(cli_workflow_env, ["session", "complete", session_id], extra_env=env_vars)
        # After completion, files are restored to global queues
        task_validated = cli_workflow_env["tasks_root"] / "validated" / f"{task_id}.md"
        qa_done = cli_workflow_env["qa_root"] / "done" / f"{task_id}-qa.md"
        assert task_validated.exists()
        assert qa_done.exists()
        session_validated = cli_workflow_env["sessions_root"] / "validated" / session_id / "session.json"
        assert session_validated.exists(), "Session file should move to validated/"
        session_data = json.loads(session_validated.read_text())
        assert session_data["meta"]["status"] == "validated"
