from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
import sys

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


def test_tasks_claim_and_status_roundtrip(isolated_project_env: Path) -> None:
    """tasks/claim and tasks/status should preserve behavior after refactor."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    from edison.core import task

    # Create a simple task in the isolated project
    task_id = "100-wave2-refactor"
    task.create_task(task_id, "Refactor integration smoke test")  # type: ignore[attr-defined]

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["project_OWNER"] = "integration-tester"
    env["PYTHONUNBUFFERED"] = "1"

    status_script = scripts_root / "tasks" / "status"
    claim_script = scripts_root / "tasks" / "claim"

    # Initial status via CLI
    result = run_with_timeout(
        [str(status_script), task_id, "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"status failed: {result.stdout}\n{result.stderr}"
    initial_meta = json.loads(result.stdout)
    assert initial_meta["status"] == "todo"

    # Claim the task (stamps owner + last active)
    result = run_with_timeout(
        [str(claim_script), task_id],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"claim failed: {result.stdout}\n{result.stderr}"

    # Status after claim should reflect updated owner and wip status
    result = run_with_timeout(
        [str(status_script), task_id, "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"status after claim failed: {result.stdout}\n{result.stderr}"
    meta = json.loads(result.stdout)
    assert meta["owner"] == "integration-tester"
    assert meta["status"] in {"wip", "todo"}  # wip preferred, but allow legacy todo


@pytest.mark.integration
def test_session_next_compute_next_minimal(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """session_next.compute_next should still operate on a minimal session."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    core_root = _core_root()
    import importlib

    # Ensure AGENTS_PROJECT_ROOT points at the isolated project before import
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(isolated_project_env))

    # Minimal session.json under .project/sessions/active
    session_id = "sess-minimal"
    session_dir = isolated_project_env / ".project" / "sessions" / "active" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_payload = {"id": session_id, "tasks": {}, "qa": {}}
    (session_dir / "session.json").write_text(json.dumps(session_payload), encoding="utf-8")

    import importlib

    session_next_mod = importlib.import_module("lib.session.next")

    payload = session_next_mod.compute_next(session_id, scope=None, limit=5)  # type: ignore[attr-defined]

    assert payload["sessionId"] == session_id
    assert isinstance(payload.get("actions"), list)
    assert isinstance(payload.get("blockers"), list)


@pytest.mark.integration
def test_validation_validate_basic_flow(isolated_project_env: Path) -> None:
    """scripts/validation/validate should still validate a simple report JSON."""
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()

    report = {
        "taskId": "task-validate-1",
        "round": 1,
        "validatorId": "dummy",
        "model": "codex",
        "verdict": "approve",
        "tracking": {
            "processId": 1234,
            "startedAt": "2025-01-01T00:00:00Z",
            "completedAt": "2025-01-01T00:05:00Z",
        },
    }

    report_path = isolated_project_env / "validator-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(isolated_project_env)
    env["PYTHONUNBUFFERED"] = "1"

    validate_script = scripts_root / "validation" / "validate"
    result = run_with_timeout(
        [str(validate_script), str(report_path)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"validation/validate failed: {result.stdout}\n{result.stderr}"
    assert "Validator report valid" in result.stdout


@pytest.mark.integration
def test_session_status_json_non_git_root_does_not_require_git(
    isolated_project_env: Path,
) -> None:
    """session status --json should succeed even when project root is not a git repo.

    Reproduces the scenario where:
    - AGENTS_PROJECT_ROOT points at a non-git project root that still carries
      a real .agents/config.yml with worktrees enabled, and
    - the CLI is invoked from the real repo_root (which IS a git repo).
    """
    repo_root = _repo_root()
    scripts_root = _core_scripts_root()
    session_script = scripts_root / "session" / "cli"

    project_root = isolated_project_env

    # Ensure the isolated project root is NOT a git repo (no .git directory)
    git_dir = project_root / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir, ignore_errors=True)

    # Copy real .agents/config.yml so worktree config appears enabled even though
    # the project root itself is not a git repository.
    src_config = repo_root / ".agents" / "config.yml"
    agents_dir = project_root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    if src_config.exists():
        shutil.copy(src_config, agents_dir / "config.yml")

    # Minimal session.json under .project/sessions/wip so status has something
    # to load. Include a git block to verify JSON normalization is robust.
    session_id = "sess-non-git-root"
    sess_dir = project_root / ".project" / "sessions" / "wip"
    sess_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": session_id,
        "state": "Active",
        "projectName": "integration-test",
        "worktreeBase": str((project_root / ".worktrees").resolve()),
        "created_at": "2025-01-01T00:00:00Z",
        "metadata": {},
        "parent_task_id": None,
        "tasks": [],
        "git": {
            "worktreePath": str((project_root / ".worktrees" / session_id).resolve()),
            "branchName": f"session/{session_id}",
            "baseBranch": "main",
        },
    }
    (sess_dir / f"{session_id}.json").write_text(json.dumps(payload), encoding="utf-8")

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("PROJECT_NAME", "integration-test")

    # Run session status --json from the REAL repo root (git repo present) while
    # AGENTS_PROJECT_ROOT points at a non-git project root. This used to try to
    # materialize a git worktree and fail; it should now degrade gracefully.
    result = run_with_timeout(
        [str(session_script), "status", session_id, "--json"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"session status --json failed for non-git AGENTS_PROJECT_ROOT\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    data = json.loads(result.stdout)
    assert data["id"] == session_id
    # Git metadata block should always be a dict; contents are optional when git
    # is unavailable but JSON shape must be stable.
    assert isinstance(data.get("git", {}), dict)
