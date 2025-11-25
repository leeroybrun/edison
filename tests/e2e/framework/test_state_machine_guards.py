from __future__ import annotations

import json
from pathlib import Path
import sys
import subprocess

import pytest


# Resolve repository root and helper paths
REPO_ROOT = Path(__file__).resolve().parents[6]
E2E_DIR = REPO_ROOT / ".edison" / "core" / "tests" / "e2e"
HELPERS_DIR = E2E_DIR / "helpers"
for p in (E2E_DIR, HELPERS_DIR):
    if str(p) not in sys.path:

from helpers.test_env import TestProjectDir  # type: ignore
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_output_contains,
)
from edison.core.utils.subprocess import run_with_timeout


def _import_task():
    core_root = REPO_ROOT / ".edison" / "core"
    scripts_root = core_root / "scripts"
    for p in (core_root, scripts_root):
        if str(p) not in sys.path:
    from edison.core import task  # type: ignore
    return task


@pytest.mark.fast
def test_defaults_yaml_contains_state_machine():
    """defaults.yaml must define statemachine for task and qa domains."""
    import yaml
    cfg_path = REPO_ROOT / ".edison" / "core" / "defaults.yaml"
    data = yaml.safe_load(cfg_path.read_text())
    assert "statemachine" in data, "defaults.yaml missing 'statemachine' section"
    sm = data["statemachine"]
    assert "task" in sm and "qa" in sm, "statemachine must include task and qa"
    for domain in ("task", "qa"):
        assert "states" in sm[domain], f"{domain} state machine incomplete"
        states = sm[domain]["states"]
        assert isinstance(states, dict) and states, f"{domain} states must be a mapping"
        assert all("allowed_transitions" in (info or {}) for info in states.values())


@pytest.mark.fast
def test_task_validate_state_transition_basic():
    task = _import_task()

    ok, msg = task.validate_state_transition("task", "todo", "wip")
    assert ok, f"todo→wip should be allowed; got: {msg}"

    ok, msg = task.validate_state_transition("task", "todo", "validated")
    assert not ok, "todo→validated must be rejected"
    assert "allowed" in msg.lower() or "invalid" in msg.lower()

    ok, msg = task.validate_state_transition("qa", "waiting", "todo")
    assert ok, f"QA waiting→todo should be allowed; got: {msg}"

    ok, msg = task.validate_state_transition("qa", "todo", "validated")
    assert not ok, "QA todo→validated must be rejected"


@pytest.mark.task
def test_tasks_status_blocks_invalid_skip(tmp_path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)

    # Create a task via real CLI (starts in todo)
    res_new = run_script(
        "tasks/new",
        ["--id", "450", "--wave", "wave2", "--slug", "guards"],
        cwd=proj.tmp_path,
    )
    assert_command_success(res_new)
    task_id = "450-wave2-guards"

    # Attempt illegal skip: todo → validated
    res_skip = run_script(
        "tasks/status",
        [task_id, "--status", "validated"],
        cwd=proj.tmp_path,
    )
    assert_command_failure(res_skip)
    assert_output_contains(res_skip, "Invalid transition", in_stderr=True)

@pytest.mark.task
def test_ready_requires_impl_report(tmp_path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    # Create a task
    res_new = run_script(
        "tasks/new",
        ["--id", "451", "--wave", "wave2", "--slug", "guards-ready"],
        cwd=proj.tmp_path,
    )
    assert_command_success(res_new)
    task_id = "451-wave2-guards-ready"
    # Prepare a minimal session to satisfy --session
    (proj.project_root / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    (proj.project_root / "sessions" / "wip" / "s-guards.json").write_text(json.dumps({
        "meta": {"sessionId": "s-guards", "createdAt": "2025-01-01T00:00:00Z", "lastActive": "2025-01-01T00:00:00Z"},
        "tasks": {}, "qa": {}, "activityLog": []
    }, indent=2))

    # Ready should fail when no implementation report exists
    res_ready = run_script(
        "tasks/ready",
        [task_id, "--session", "s-guards"],
        cwd=proj.tmp_path,
    )
    assert_command_failure(res_ready)
    msg = (res_ready.stderr + res_ready.stdout)
    assert (
        ("Implementation report required" in msg)
        or ("guard fails closed" in msg.lower())
        or ("validators/config.json" in msg)  # legacy wording (backward-compatible)
        or ("config/validators.yml" in msg)   # new YAML-only path
    ), f"unexpected ready failure output:\n{msg}"


@pytest.mark.task
def test_precommit_checker_cli_blocks_invalid_pair(tmp_path):
    """Invoke pre-commit checker module in pair-check mode to validate logic."""
    # Simulate a rename pair: task todo → validated (should fail)
    checker = REPO_ROOT / ".edison" / "core" / "scripts" / "git-hooks" / "precommit_check.py"
    assert checker.exists(), "precommit_check.py not found (must be added by implementation)"

    # Run as: python precommit_check.py --check-pair task:todo:validated
    result = run_with_timeout(
        ["python3", str(checker), "--check-pair", "task:todo:validated"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, f"checker should fail invalid pair; output: {result.stdout}\n{result.stderr}"
    assert "Invalid transition" in (result.stderr or result.stdout)


@pytest.mark.task
def test_missing_status_line_fails_update(tmp_path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    # Create minimal malformed task file without Status line
    tid = "460-wave2-missing-status"
    bad = proj.project_root / "tasks" / "todo" / f"{tid}.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("# Broken Task\n- **Owner:** tester\n\n")

    res = run_script(
        "tasks/status",
        [tid, "--status", "wip"],
        cwd=proj.tmp_path,
    )
    assert_command_failure(res)
    assert "Could not find Status line" in (res.stderr + res.stdout)


@pytest.mark.task
def test_concurrent_lock_blocks_move(tmp_path):
    proj = TestProjectDir(tmp_path, REPO_ROOT)
    # Create a normal task
    res_new = run_script(
        "tasks/new",
        ["--id", "461", "--wave", "wave2", "--slug", "locks"],
        cwd=proj.tmp_path,
    )
    assert_command_success(res_new)
    task_id = "461-wave2-locks"
    # Place a lock on the destination directory path (wip/<file>.lock) to simulate concurrent update
    dest = proj.project_root / "tasks" / "wip" / f"{task_id}.md"
    lock = dest.with_suffix(dest.suffix + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("lock")
    try:
        res = run_script(
            "tasks/status",
            [task_id, "--status", "wip"],
            cwd=proj.tmp_path,
        )
        assert_command_failure(res)
        assert ("destination locked" in (res.stderr + res.stdout)) or ("locked" in (res.stderr + res.stdout).lower())
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


@pytest.mark.fast
def test_validator_rejects_missing_current_status():
    task = _import_task()
    ok, msg = task.validate_state_transition("task", "", "wip")
    assert not ok and "Missing current status" in msg


@pytest.mark.fast
def test_all_valid_adjacencies_allowed_by_validator():
    import yaml
    cfg = yaml.safe_load((REPO_ROOT / ".edison" / "core" / "defaults.yaml").read_text())
    sm = cfg["statemachine"]
    task = _import_task()
    for domain in ("task", "qa"):
        states = sm[domain]["states"]
        for cur, info in states.items():
            nexts = [t.get("to") for t in info.get("allowed_transitions", [])]
            for nxt in nexts:
                ok, msg = task.validate_state_transition(domain, cur, nxt)
                assert ok, f"expected allowed {domain} {cur}→{nxt}, got: {msg}"
