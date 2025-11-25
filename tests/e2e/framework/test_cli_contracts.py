#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from edison.core.utils.subprocess import run_with_timeout


def get_repo_root() -> Path:
    """Resolve the outer project git root for CLI contract tests.

    When running inside the nested `.edison` git repository, prefer the
    parent project root so `.project/` and `.agents/` resolve correctly.
    """
    current = Path(__file__).resolve()
    candidate: Optional[Path] = None
    while current != current.parent:
        if (current / ".git").exists():
            candidate = current
        current = current.parent
    if candidate is None:
        raise RuntimeError("Could not find repository root")
    if candidate.name == ".edison" and (candidate.parent / ".git").exists():
        return candidate.parent
    return candidate


REPO_ROOT = get_repo_root()
SCRIPTS_ROOT = REPO_ROOT / ".edison" / "core" / "scripts"


def run(cli: list[str], cwd: Optional[Path] = None):
    env = os.environ.copy()
    # Ensure scripts resolve repo-relative paths in tests
    env["AGENTS_PROJECT_ROOT"] = str(REPO_ROOT)
    proc = run_with_timeout(cli, cwd=cwd or REPO_ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_tasks_status_stdout_human():
    sample_task = str((REPO_ROOT / ".project" / "tasks" / "todo").glob("*.md").__iter__().__next__())
    rc, out, err = run([str(SCRIPTS_ROOT / "tasks" / "status"), "--path", sample_task])
    assert rc == 0
    # Human-readable metadata goes to stdout
    assert "Status" in out and "Owner" in out
    # No JSON noise mixed into human output
    assert not out.strip().startswith("{")


def test_tasks_status_json_pure_stdout():
    sample_task = str((REPO_ROOT / ".project" / "tasks" / "todo").glob("*.md").__iter__().__next__())
    rc, out, err = run([str(SCRIPTS_ROOT / "tasks" / "status"), "--path", sample_task, "--json"])
    assert rc == 0
    # Pure JSON on stdout
    obj = json.loads(out)
    assert isinstance(obj, dict)
    assert obj.get("recordType") in {"task", "qa"}
    # No logs on stdout
    assert "✅" not in out and "❌" not in out


def test_tasks_status_json_error_schema():
    rc, out, err = run([str(SCRIPTS_ROOT / "tasks" / "status"), "--path", str(REPO_ROOT / "nope.md"), "--json"])
    assert rc != 0
    obj = json.loads(out)
    assert set(obj.keys()) >= {"error", "code"}


def test_qa_promote_json_error_schema():
    rc, out, err = run([str(SCRIPTS_ROOT / "qa" / "promote"), "--task", "no-such-task-xyz", "--to", "todo", "--json"])
    assert rc != 0
    obj = json.loads(out)
    assert set(obj.keys()) >= {"error", "code"}


def test_session_status_json_pure():
    # Pick an existing test session id
    session_id = "sandbox-test"
    rc, out, err = run([str(SCRIPTS_ROOT / "session"), "status", session_id, "--json"])
    assert rc == 0
    obj = json.loads(out)
    assert isinstance(obj, dict) and "meta" in obj
    # Ensure no human guidance in stdout
    assert "Next steps" not in out


def test_session_heartbeat_logs_to_stderr():
    session_id = "sandbox-test"
    rc, out, err = run([str(SCRIPTS_ROOT / "session"), "heartbeat", session_id])
    assert rc == 0
    # Heartbeat is a log → stderr; stdout must be empty
    assert out.strip() == ""
    assert "heartbeat" in err


def test_validators_validate_emits_summary_path_on_stdout_and_logs_to_stderr(tmp_path: Path = None):
    task_id = "contract-test-task"
    # Create an empty evidence dir (no reports → failure path)
    ev_dir = REPO_ROOT / ".project" / "qa" / "validation-evidence" / task_id
    (ev_dir / "round-1").mkdir(parents=True, exist_ok=True)
    rc, out, err = run([str(SCRIPTS_ROOT / "validators" / "validate"), "--task", task_id])
    # Should fail due to missing reports
    assert rc != 0
    # stdout should contain path to bundle-approved.json (single line acceptable)
    summary_path = (ev_dir / "round-1" / "bundle-approved.json")
    assert str(summary_path) in out
    assert summary_path.exists()
    # stderr should mention missing reports
    assert "missing report" in err.lower() or "bundle not approved" in err.lower()


def test_delegation_validate_config_json_mode():
    cfg = str(REPO_ROOT / ".edison" / "core" / "delegation" / "config.json")
    validate_cli = REPO_ROOT / ".edison" / "core" / "scripts" / "delegation" / "validate"
    rc, out, err = run([str(validate_cli), "config", "--path", cfg, "--json"])
    assert rc == 0
    obj = json.loads(out)
    assert obj.get("valid") is True
    assert err.strip() == ""


def test_delegation_validate_report_json_error():
    validate_cli = REPO_ROOT / ".edison" / "core" / "scripts" / "delegation" / "validate"
    rc, out, err = run([str(validate_cli), "report", str(REPO_ROOT / "nope.json"), "--json"])
    assert rc != 0
    obj = json.loads(out)
    assert obj.get("code") in {"FILE_NOT_FOUND", "INVALID_JSON"}


def test_implementation_report_help_mentions_contracts():
    rc, out, err = run(["python3", str(SCRIPTS_ROOT / "implementation" / "report"), "--help"])
    assert rc == 0
    # Help should inform stdout/stderr separation contract
    assert "stdout" in out.lower() and "stderr" in out.lower()