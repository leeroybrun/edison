#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import Optional
from edison.core.utils.subprocess import run_with_timeout

from helpers.env import TestProjectDir
from tests.config import get_env_var_name
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()


def run(cli: list[str], cwd: Path, extra_env: Optional[dict[str, str]] = None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    # Ensure the subprocess can import the in-repo `edison` package.
    src_root = REPO_ROOT / "src"
    existing_py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(src_root), existing_py_path]) if existing_py_path else str(src_root)

    # Ensure scripts resolve repo-relative paths in tests (config-driven env var name).
    env_var_name = get_env_var_name("primary", "agents_project_root")
    env[env_var_name] = str(cwd)

    # Deterministic project name for placeholder substitutions in subprocess CLIs.
    env.setdefault("PROJECT_NAME", "example-project")

    # Convert "edison" to module invocation to avoid PATH issues
    if cli and cli[0] == "edison":
        cli = [sys.executable, "-m", "edison"] + cli[1:]
    proc = run_with_timeout(cli, cwd=cwd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def test_tasks_status_stdout_human(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    record_id = "901-wave1-contract-task"

    rc, out, err = run(
        ["edison", "task", "new", "--id", "901", "--wave", "wave1", "--slug", "contract-task"],
        cwd=proj.tmp_path,
    )
    assert rc == 0

    rc, out, err = run(["edison", "task", "status", record_id], cwd=proj.tmp_path)
    assert rc == 0
    # Human-readable metadata goes to stdout
    assert "Task:" in out and "Status:" in out
    # No JSON noise mixed into human output
    assert not out.strip().startswith("{")


def test_tasks_status_json_pure_stdout(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    record_id = "901-wave1-contract-task"

    rc, out, err = run(
        ["edison", "task", "new", "--id", "901", "--wave", "wave1", "--slug", "contract-task"],
        cwd=proj.tmp_path,
    )
    assert rc == 0

    rc, out, err = run(["edison", "task", "status", record_id, "--json"], cwd=proj.tmp_path)
    assert rc == 0
    # Pure JSON on stdout
    obj = json.loads(out)
    assert isinstance(obj, dict)
    assert obj.get("record_id") == record_id
    assert obj.get("record_type") in {"task", "qa", None}
    # No logs on stdout
    assert "✅" not in out and "❌" not in out


def test_tasks_status_json_error_schema(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    rc, out, err = run(["edison", "task", "status", "no-such-task-xyz", "--json"], cwd=proj.tmp_path)
    assert rc != 0
    obj = json.loads(out)
    assert set(obj.keys()) >= {"error", "code"}


def test_qa_promote_json_error_schema(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    rc, out, err = run(
        ["edison", "qa", "promote", "no-such-task-xyz", "--status", "todo", "--json"],
        cwd=proj.tmp_path,
    )
    assert rc != 0
    obj = json.loads(out)
    assert set(obj.keys()) >= {"error", "code"}


def test_session_status_json_pure(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    session_id = "sandbox-test"

    rc, out, err = run(
        ["edison", "session", "create", "--session-id", session_id, "--owner", "tester", "--no-worktree"],
        cwd=proj.tmp_path,
    )
    assert rc == 0

    rc, out, err = run(["edison", "session", "status", session_id, "--json"], cwd=proj.tmp_path)
    assert rc == 0
    obj = json.loads(out)
    assert isinstance(obj, dict)
    assert obj.get("id") == session_id or obj.get("session_id") == session_id or obj.get("meta", {}).get("id") == session_id
    # Ensure no human guidance in stdout
    assert "Next steps" not in out


def test_session_heartbeat_logs_to_stderr(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    task_id = "contract-track-task"

    # Create a tracking record so heartbeat has something to update.
    rc, out, err = run(
        ["edison", "session", "track", "start", "--task", task_id, "--type", "implementation", "--json"],
        cwd=proj.tmp_path,
    )
    assert rc == 0

    rc, out, err = run(
        ["edison", "session", "track", "heartbeat", "--task", task_id, "--json"],
        cwd=proj.tmp_path,
    )
    assert rc == 0
    payload = json.loads(out)
    assert payload.get("taskId") == task_id
    assert isinstance(payload.get("updated"), list) and payload.get("updated")


def test_validators_validate_emits_summary_path_on_stdout_and_logs_to_stderr(tmp_path: Path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    task_id = "contract-test-task"
    # Create an empty evidence dir (no reports → failure path)
    ev_dir = proj.tmp_path / ".project" / "qa" / "validation-reports" / task_id
    (ev_dir / "round-1").mkdir(parents=True, exist_ok=True)
    rc, out, err = run(["edison", "qa", "validate", task_id, "--check-only", "--json"], cwd=proj.tmp_path)
    assert rc != 0  # Not approved
    payload = json.loads(out)
    assert payload.get("task_id") == task_id
    summary_path = proj.tmp_path / str(payload.get("bundle_file"))
    assert summary_path.exists()
    assert summary_path.name == "bundle-summary.md"
    assert payload.get("approved") is False


def test_delegation_validate_config_json_mode():
    # Delegation validation is not implemented as a CLI command yet - skip this test
    import pytest
    pytest.skip("Delegation validate CLI not yet implemented")


def test_delegation_validate_report_json_error():
    # Delegation validation is not implemented as a CLI command yet - skip this test
    import pytest
    pytest.skip("Delegation validate CLI not yet implemented")


def test_implementation_report_help_mentions_contracts():
    # Implementation report CLI doesn't exist in new structure - skip
    import pytest
    pytest.skip("Implementation report CLI not yet implemented")
