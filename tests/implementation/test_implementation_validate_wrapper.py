from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from edison.core.utils.subprocess import run_with_timeout


REPO_ROOT = Path(__file__).resolve().parents[4]
WRAPPER = REPO_ROOT / "scripts" / "implementation" / "validate"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return run_with_timeout([str(WRAPPER)] + args, capture_output=True, text=True)


def test_wrapper_exists_and_executable():
    assert WRAPPER.exists(), f"Missing wrapper: {WRAPPER}"
    st = WRAPPER.stat()
    assert bool(st.st_mode & stat.S_IXUSR), "Wrapper is not executable"


def test_wrapper_invalid_json_decode(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{" )  # malformed JSON
    res = _run([str(bad)])
    assert res.returncode != 0
    assert "Invalid JSON" in res.stdout or "Invalid JSON" in res.stderr


def test_wrapper_schema_failure(tmp_path: Path):
    # Valid JSON, wrong schema (missing required fields)
    bad = tmp_path / "schema-bad.json"
    bad.write_text('{"taskId":"x"}')
    res = _run([str(bad)])
    assert res.returncode != 0
    # Expect schema error mention
    assert "Schema errors" in res.stdout or "missing required field" in res.stdout


def test_wrapper_schema_success(tmp_path: Path):
    ok = tmp_path / "good.json"
    # Minimal valid example respecting required fields from schema
    ok.write_text(
        {
            "taskId": "demo-123",
            "round": 1,
            "implementationApproach": "orchestrator-direct",
            "primaryModel": "claude",
            "completionStatus": "partial",
            "followUpTasks": [],
            "notesForValidator": "",
            "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z"}
        }.__repr__().replace("'", '"')
    )
    res = _run([str(ok)])
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Implementation report valid" in res.stdout