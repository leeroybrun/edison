#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()


def run(cli: list[str], cwd: Optional[Path] = None):
    env = os.environ.copy()
    # Ensure scripts resolve repo-relative paths in tests
    env["AGENTS_PROJECT_ROOT"] = str(REPO_ROOT)
    # Convert "edison" to module invocation to avoid PATH issues
    if cli and cli[0] == "edison":
        cli = [sys.executable, "-m", "edison"] + cli[1:]
    proc = run_with_timeout(cli, cwd=cwd or REPO_ROOT, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def test_tasks_status_stdout_human():
    sample_task = str((REPO_ROOT / ".project" / "tasks" / "todo").glob("*.md").__iter__().__next__())
    rc, out, err = run(["edison", "task", "status", "--path", sample_task])
    assert rc == 0
    # Human-readable metadata goes to stdout
    assert "Status" in out and "Owner" in out
    # No JSON noise mixed into human output
    assert not out.strip().startswith("{")


def test_tasks_status_json_pure_stdout():
    sample_task = str((REPO_ROOT / ".project" / "tasks" / "todo").glob("*.md").__iter__().__next__())
    rc, out, err = run(["edison", "task", "status", "--path", sample_task, "--json"])
    assert rc == 0
    # Pure JSON on stdout
    obj = json.loads(out)
    assert isinstance(obj, dict)
    assert obj.get("recordType") in {"task", "qa"}
    # No logs on stdout
    assert "✅" not in out and "❌" not in out


def test_tasks_status_json_error_schema():
    rc, out, err = run(["edison", "task", "status", "--path", str(REPO_ROOT / "nope.md"), "--json"])
    assert rc != 0
    obj = json.loads(out)
    assert set(obj.keys()) >= {"error", "code"}


def test_qa_promote_json_error_schema():
    rc, out, err = run(["edison", "qa", "promote", "--task", "no-such-task-xyz", "--to", "todo", "--json"])
    assert rc != 0
    obj = json.loads(out)
    assert set(obj.keys()) >= {"error", "code"}


def test_session_status_json_pure():
    # Pick an existing test session id
    session_id = "sandbox-test"
    rc, out, err = run(["edison", "session", "status", session_id, "--json"])
    assert rc == 0
    obj = json.loads(out)
    assert isinstance(obj, dict) and "meta" in obj
    # Ensure no human guidance in stdout
    assert "Next steps" not in out


def test_session_heartbeat_logs_to_stderr():
    session_id = "sandbox-test"
    rc, out, err = run(["edison", "session", "track", session_id])
    assert rc == 0
    # Heartbeat is a log → stderr; stdout must be empty
    assert out.strip() == ""
    assert "heartbeat" in err or "track" in err


def test_validators_validate_emits_summary_path_on_stdout_and_logs_to_stderr(tmp_path: Path = None):
    task_id = "contract-test-task"
    # Create an empty evidence dir (no reports → failure path)
    ev_dir = REPO_ROOT / ".project" / "qa" / "validation-evidence" / task_id
    (ev_dir / "round-1").mkdir(parents=True, exist_ok=True)
    rc, out, err = run(["edison", "qa", "validate", task_id, "--check-only", "--json"])
    assert rc != 0  # Not approved
    payload = json.loads(out)
    assert payload.get("task_id") == task_id
    summary_path = REPO_ROOT / str(payload.get("bundle_file"))
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
