from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest
from edison.core.utils.subprocess import run_with_timeout


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        # Prefer real project root, not the inner .edison Git repo
        if parent.name == ".edison":
            continue
        if (parent / ".git").exists():
            return parent
    raise AssertionError("cannot locate repository root for integration tests")


def _core_scripts_root() -> Path:
    return _repo_root() / ".edison" / "core" / "scripts"


def _sandbox_env(base: Path) -> Dict[str, str]:
    env = os.environ.copy()
    # Direct core libraries that rely on AGENTS_PROJECT_ROOT to the sandbox
    env["AGENTS_PROJECT_ROOT"] = str(base)
    # Keep output deterministic for assertions
    env["PYTHONUNBUFFERED"] = "1"
    return env


@pytest.mark.integration
@pytest.mark.security
def test_ci_run_rejects_shell_injection_in_rest_args(tmp_path: Path) -> None:
    """RED: ci/run must not treat rest args as shell snippets."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    sandbox = tmp_path / "ci-sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    sentinel = sandbox / "ci-injected.txt"

    env = _sandbox_env(sandbox)
    # Configure a simple CI command via environment-only overrides so tests
    # do not depend on project config structure.
    env["EDISON_ci_commands_test"] = (
        'python3 -c "import pathlib; pathlib.Path(\'ci-ok.txt\').write_text(\'ok\')"'
    )

    ci_script = scripts_root / "ci" / "run"

    # Attempt to smuggle a second command via shell metacharacters in rest args.
    # With the current implementation (shell=True), this will create the
    # sentinel file; the secure refactor must prevent that.
    result = run_with_timeout(
        [str(ci_script), "test", ";", "touch", str(sentinel)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    # RED expectation (will currently fail): no injected file should be created.
    assert result.returncode != 0 or result.returncode == 0  # command may succeed or fail
    assert not sentinel.exists(), "ci/run allowed shell injection via rest args"


@pytest.mark.integration
@pytest.mark.security
def test_migrate_session_db_rejects_shell_injection(tmp_path: Path) -> None:
    """RED: migrate-session-db must not execute injected shell commands."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    sandbox = tmp_path / "db-migrate-sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    sentinel = sandbox / "migrate-injected.txt"

    env = _sandbox_env(sandbox)
    # Force database.enabled=true so the script does not short‑circuit.
    env["EDISON_database_enabled"] = "true"
    # Inject a second command via shell metacharacters in the configured command.
    env["EDISON_ci_commands_migrate"] = (
        f'python3 -c "import pathlib; pathlib.Path(\'migrate-ok.txt\').write_text(\'ok\')" ; touch {sentinel}'
    )

    script = scripts_root / "db" / "migrate-session-db"
    result = run_with_timeout(
        [str(script)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    # RED expectation: regardless of exit code, injected touch must never run.
    assert result.returncode != 0 or result.returncode == 0
    assert not sentinel.exists(), "migrate-session-db allowed shell injection from config command"


@pytest.mark.integration
@pytest.mark.security
def test_seed_session_db_rejects_shell_injection(tmp_path: Path) -> None:
    """RED: seed-session-db must not execute injected shell commands."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    sandbox = tmp_path / "db-seed-sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    sentinel = sandbox / "seed-injected.txt"

    env = _sandbox_env(sandbox)
    env["EDISON_database_enabled"] = "true"
    env["EDISON_ci_commands_seed"] = (
        f'python3 -c "import pathlib; pathlib.Path(\'seed-ok.txt\').write_text(\'ok\')" ; touch {sentinel}'
    )

    script = scripts_root / "db" / "seed-session-db"
    result = run_with_timeout(
        [str(script)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0 or result.returncode == 0
    assert not sentinel.exists(), "seed-session-db allowed shell injection from config command"


@pytest.mark.integration
def test_cli_utils_json_output_schema() -> None:
    """RED: cli_utils.json_output must expose the canonical JSON schema."""
    from edison.core import cli_utils  # type: ignore[attr-defined]

    payload = cli_utils.json_output(
        success=False,
        data={"step": "ci"},
        error={"message": "boom", "code": "CI_FAILED", "context": {"detail": "test"}},
    )
    obj = json.loads(payload)

    assert isinstance(obj, dict)
    assert set(obj.keys()) == {"success", "data", "error"}
    assert obj["success"] is False
    assert isinstance(obj["data"], dict)
    assert obj["data"]["step"] == "ci"
    assert isinstance(obj["error"], dict)
    assert obj["error"]["message"] == "boom"
    assert obj["error"]["code"] == "CI_FAILED"
    assert isinstance(obj["error"]["context"], dict)
    assert obj["error"]["context"]["detail"] == "test"


@pytest.mark.integration
def test_cli_utils_error_uses_json_contract_in_json_mode(capsys) -> None:
    """RED: cli_error must emit structured JSON when json_mode is True."""
    from edison.core import cli_utils  # type: ignore[attr-defined]

    code = cli_utils.cli_error("bad", "TEST_ERROR", json_mode=True)
    captured = capsys.readouterr()

    assert code != 0
    data = json.loads(captured.out or "{}")
    assert data.get("success") is False
    err = data.get("error") or {}
    assert err.get("message") == "bad"
    assert err.get("code") == "TEST_ERROR"


@pytest.mark.integration
def test_cli_utils_db_and_git_timeouts_are_enforced(tmp_path: Path) -> None:
    """RED: DB and git helpers must enforce configurable timeouts."""
    from edison.core import cli_utils  # type: ignore[attr-defined]

    slow_cmd: List[str] = ["python3", "-c", "import time; time.sleep(2)"]

    # DB timeout should raise TimeoutExpired when below sleep duration
    with pytest.raises(subprocess.TimeoutExpired):
        cli_utils.run_db_command(slow_cmd, cwd=tmp_path, timeout=0.2)

    # Git timeout should similarly raise when below sleep duration
    with pytest.raises(subprocess.TimeoutExpired):
        cli_utils.run_git_command(slow_cmd, cwd=tmp_path, timeout=0.2)


@pytest.mark.integration
def test_ci_run_emits_structured_json_on_failure(tmp_path: Path) -> None:
    """RED: ci/run --json must emit standardized JSON on failure."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    sandbox = tmp_path / "ci-json"
    sandbox.mkdir(parents=True, exist_ok=True)

    env = _sandbox_env(sandbox)
    # Intentionally configure a non-existent command so execution fails.
    env["EDISON_ci_commands_lint"] = "nonexistent-ci-binary-for-json"

    script = scripts_root / "ci" / "run"
    result = run_with_timeout(
        [str(script), "lint", "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    # RED expectation: stdout must be valid JSON with standard schema.
    obj = json.loads(result.stdout or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert "message" in err
    assert "code" in err
    assert isinstance(err.get("context", {}), dict)


@pytest.mark.integration
def test_tasks_status_json_contract(tmp_path: Path) -> None:
    """tasks/status --json emits legacy metadata JSON (no envelope)."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    # Pick an existing task in .project/tasks/todo
    sample_task = next((repo_root / ".project" / "tasks" / "todo").glob("*.md"))

    env = _sandbox_env(repo_root)
    script = scripts_root / "tasks" / "status"
    result = run_with_timeout(
        [str(script), "--path", str(sample_task), "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    obj = json.loads(result.stdout or "{}")
    # Contract: flat metadata dict with recordType/status, not wrapped in success/data/error.
    assert isinstance(obj, dict)
    assert obj.get("recordType") in {"task", "qa"}
    assert "status" in obj
    assert "success" not in obj
    assert "error" not in obj or not isinstance(obj.get("error"), dict)


@pytest.mark.integration
def test_tasks_status_json_error_contract(tmp_path: Path) -> None:
    """tasks/status --json error path returns {error, code}."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    env = _sandbox_env(repo_root)
    script = scripts_root / "tasks" / "status"
    missing = repo_root / "no-such-file-for-status.md"

    result = run_with_timeout(
        [str(script), "--path", str(missing), "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    obj = json.loads(result.stdout or "{}")
    assert obj.get("code") == "FILE_NOT_FOUND"
    assert "error" in obj


@pytest.mark.integration
def test_qa_promote_json_error_contract(tmp_path: Path) -> None:
    """qa/promote --json error path returns {error, code}."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    env = _sandbox_env(repo_root)
    script = scripts_root / "qa" / "promote"

    result = run_with_timeout(
        [str(script), "--task", "no-such-task-xyz", "--to", "todo", "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    obj = json.loads(result.stdout or "{}")
    assert obj.get("code") == "QA_NOT_FOUND"
    assert "error" in obj


@pytest.mark.integration
def test_delegation_validate_config_json_contract(tmp_path: Path) -> None:
    """delegation/validate config --json returns flat {'valid': True} JSON."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    cfg = repo_root / ".edison" / "core" / "delegation" / "config.json"
    env = _sandbox_env(repo_root)
    script = scripts_root / "delegation" / "validate"

    result = run_with_timeout(
        [str(script), "config", "--path", str(cfg), "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    obj = json.loads(result.stdout or "{}")
    assert obj.get("valid") is True
    # No top-level envelope keys from cli_utils.json_output
    assert "success" not in obj
    assert "error" not in obj


@pytest.mark.integration
def test_delegation_validate_report_json_error_contract(tmp_path: Path) -> None:
    """delegation/validate report --json returns {code, error?} for missing files."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    env = _sandbox_env(repo_root)
    script = scripts_root / "delegation" / "validate"
    missing = repo_root / "no-such-delegation-report.json"

    result = run_with_timeout(
        [str(script), "report", str(missing), "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    obj = json.loads(result.stdout or "{}")
    assert obj.get("code") in {"FILE_NOT_FOUND", "INVALID_JSON"}
    assert "error" in obj


@pytest.mark.integration
def test_session_status_json_contract(tmp_path: Path) -> None:
    """session status --json emits raw session document (no envelope)."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    env = _sandbox_env(repo_root)
    script = scripts_root / "session"
    session_id = "sess-001"

    result = run_with_timeout(
        [str(script), "status", session_id, "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    obj = json.loads(result.stdout or "{}")
    assert isinstance(obj, dict)
    # Contract: top-level session fields, not wrapped in success/data/error.
    assert obj.get("id") == session_id
    assert obj.get("state") in {"Active", "Closing", "Validated"}
    assert "success" not in obj
    assert "error" not in obj


@pytest.mark.integration
def test_migrate_session_db_emits_json_on_failure(tmp_path: Path) -> None:
    """RED: migrate-session-db --json must emit standardized JSON on failure."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    sandbox = tmp_path / "db-migrate-json"
    sandbox.mkdir(parents=True, exist_ok=True)

    env = _sandbox_env(sandbox)
    env["EDISON_database_enabled"] = "true"
    env["EDISON_ci_commands_migrate"] = "nonexistent-migrate-binary-for-json"

    script = scripts_root / "db" / "migrate-session-db"
    result = run_with_timeout(
        [str(script), "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    obj = json.loads(result.stdout or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert "message" in err
    assert "code" in err
    assert isinstance(err.get("context", {}), dict)


@pytest.mark.integration
def test_seed_session_db_emits_json_on_failure(tmp_path: Path) -> None:
    """RED: seed-session-db --json must emit standardized JSON on failure."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    sandbox = tmp_path / "db-seed-json"
    sandbox.mkdir(parents=True, exist_ok=True)

    env = _sandbox_env(sandbox)
    env["EDISON_database_enabled"] = "true"
    env["EDISON_ci_commands_seed"] = "nonexistent-seed-binary-for-json"

    script = scripts_root / "db" / "seed-session-db"
    result = run_with_timeout(
        [str(script), "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    obj = json.loads(result.stdout or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert "message" in err
    assert "code" in err
    assert isinstance(err.get("context", {}), dict)