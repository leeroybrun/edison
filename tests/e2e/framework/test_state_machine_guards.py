from __future__ import annotations

import json
from pathlib import Path
import sys
import subprocess

import pytest


# Add helpers to path for imports
TESTS_ROOT = Path(__file__).resolve().parents[2]
HELPERS_DIR = TESTS_ROOT / "e2e" / "helpers"
from test_env import TestProjectDir  # type: ignore
from command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_output_contains,
)
from edison.core.utils.subprocess import run_with_timeout
from edison.data import get_data_path

# Edison config paths (bundled in package)
EDISON_CONFIG_ROOT = get_data_path("config")


def test_defaults_yaml_contains_state_machine():
    """defaults.yaml must define statemachine for task and qa domains."""
    import yaml
    cfg_path = EDISON_CONFIG_ROOT / "defaults.yaml"
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
    from edison.core import task

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
def test_tasks_status_blocks_invalid_skip(tmp_path, isolated_project_env):
    proj = TestProjectDir(tmp_path, isolated_project_env)

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
def test_ready_requires_impl_report(tmp_path, isolated_project_env):
    proj = TestProjectDir(tmp_path, isolated_project_env)
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
@pytest.mark.skip(reason="precommit_check.py moved to git-hooks, needs refactoring")
def test_precommit_checker_cli_blocks_invalid_pair(tmp_path):
    """Invoke pre-commit checker module in pair-check mode to validate logic."""
    # TODO: Update when git-hooks integration is added
    pass


@pytest.mark.task
def test_missing_status_line_fails_update(tmp_path, isolated_project_env):
    proj = TestProjectDir(tmp_path, isolated_project_env)
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
def test_concurrent_lock_blocks_move(tmp_path, isolated_project_env):
    proj = TestProjectDir(tmp_path, isolated_project_env)
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
    from edison.core import task
    ok, msg = task.validate_state_transition("task", "", "wip")
    assert not ok and "Missing current status" in msg


@pytest.mark.fast
def test_all_valid_adjacencies_allowed_by_validator():
    import yaml
    cfg = yaml.safe_load((EDISON_CONFIG_ROOT / "defaults.yaml").read_text())
    sm = cfg["statemachine"]
    from edison.core import task
    for domain in ("task", "qa"):
        states = sm[domain]["states"]
        for cur, info in states.items():
            nexts = [t.get("to") for t in info.get("allowed_transitions", [])]
            for nxt in nexts:
                ok, msg = task.validate_state_transition(domain, cur, nxt)
                assert ok, f"expected allowed {domain} {cur}→{nxt}, got: {msg}"
