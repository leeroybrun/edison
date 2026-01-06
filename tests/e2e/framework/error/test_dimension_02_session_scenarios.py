"""DIMENSION 2: Session lifecycle scenario coverage (modern Edison CLI).

This suite exercises the core session lifecycle behaviors using the current
`python -m edison` CLI entrypoint:
  - Session creation (no worktree)
  - Task creation + claim isolation under session scope
  - Session close/timeout cleanup restoring records to global queues
  - Session recovery utilities (nested `edison session recovery ...` commands)
  - Session tracking subcommands (start/heartbeat)

These tests are intentionally filesystem-real (no mocked repos, no fabricated
legacy markdown). Any required project structure is created via shared E2E
fixtures (`create_project_structure`, `copy_templates`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from edison.core.utils.subprocess import run_with_timeout
from edison.core.utils.text import format_frontmatter
from tests.config import get_default_value
from tests.e2e.base import copy_templates, create_project_structure, setup_base_environment
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.paths import get_repo_root


REPO_ROOT = get_repo_root()


@pytest.fixture
def session_scenario_env(tmp_path: Path) -> dict:
    create_project_structure(tmp_path)
    copy_templates(tmp_path)
    env = setup_base_environment(tmp_path, owner="test-user")
    return {"tmp": tmp_path, "env": env}


def run_edison(env_data: dict, args: list[str], *, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "edison", *args]
    env_vars = dict(env_data["env"])

    # Ensure subprocess can import in-repo `edison` package.
    src_root = REPO_ROOT / "src"
    existing = env_vars.get("PYTHONPATH", "")
    py_parts = [str(src_root)]
    if existing:
        py_parts.append(existing)
    env_vars["PYTHONPATH"] = os.pathsep.join(py_parts)

    res = run_with_timeout(
        cmd,
        cwd=env_data["tmp"],
        env=env_vars,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and res.returncode != 0:
        raise AssertionError(
            f"Command failed ({res.returncode})\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{res.stdout}\n"
            f"STDERR:\n{res.stderr}"
        )
    return res


def test_scenario_01_normal_flow(session_scenario_env: dict) -> None:
    """Normal flow: create session → create+claim task → close session (restore to global)."""
    sid = "test-normal-flow"
    run_edison(
        session_scenario_env,
        ["session", "create", "--owner", "test-user", "--session-id", sid, "--mode", "start", "--no-worktree"],
    )

    run_edison(session_scenario_env, ["task", "new", "--id", "100", "--wave", "wave1", "--slug", "normal"])
    task_id = "100-wave1-normal"

    run_edison(session_scenario_env, ["task", "claim", task_id, "--session", sid])

    # Isolated under session scope
    session_task = session_scenario_env["tmp"] / ".project" / "sessions" / "wip" / sid / "tasks" / "wip" / f"{task_id}.md"
    assert session_task.exists()

    # Prepare evidence + validator approvals so the session can close (verification is strict).
    ev_round = session_scenario_env["tmp"] / ".project" / "qa" / "validation-reports" / task_id / "round-1"
    ev_round.mkdir(parents=True, exist_ok=True)

    # Do NOT hardcode bundled preset contents in tests.
    # Instead, compute required evidence + blocking validators from the current config.
    from edison.core.qa.policy.resolver import ValidationPolicyResolver
    from edison.core.registries.validators import ValidatorRegistry

    # Evidence requirements for QA promotion are computed from the default policy
    # (preset inference/defaultPreset), not from the explicit `qa validate --preset` flag.
    policy = ValidationPolicyResolver(project_root=session_scenario_env["tmp"]).resolve_for_task(
        task_id,
        session_id=sid,
    )

    def _filename_for_pattern(pattern: str) -> str:
        # Create a concrete filename that matches common glob patterns.
        import re

        name = str(pattern).strip().replace("*", "x").replace("?", "x")
        name = re.sub(r"\[[^\]]+\]", "x", name)
        return name or "evidence.txt"

    for pattern in (policy.required_evidence or []):
        fname = _filename_for_pattern(str(pattern))
        target = ev_round / fname
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok\n", encoding="utf-8")

    (ev_round / "implementation-report.md").write_text(
        format_frontmatter(
            {
                "taskId": task_id,
                "round": 1,
                "implementationApproach": "orchestrator-direct",
                "primaryModel": "codex",
                "completionStatus": "complete",
                "followUpTasks": [],
                "notesForValidator": "ok",
                "tracking": {"processId": 1, "startedAt": "t", "completedAt": "t2"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    roster = ValidatorRegistry(project_root=session_scenario_env["tmp"]).build_execution_roster(
        task_id=task_id,
        session_id=sid,
        preset_name="strict",
    )
    candidates = (
        (roster.get("alwaysRequired") or [])
        + (roster.get("triggeredBlocking") or [])
        + (roster.get("triggeredOptional") or [])
        + (roster.get("extraAdded") or [])
    )
    blocking_ids = sorted(
        {
            str(v.get("id"))
            for v in candidates
            if isinstance(v, dict) and v.get("blocking") and v.get("id")
        }
    )
    if not blocking_ids:
        raise AssertionError("Test requires at least one blocking validator in strict preset.")

    for vid in blocking_ids:
        model = "claude" if vid == "global-claude" else "codex"
        (ev_round / f"validator-{vid}-report.md").write_text(
            format_frontmatter(
                {
                    "taskId": task_id,
                    "round": 1,
                    "validatorId": vid,
                    "model": model,
                    "verdict": "approve",
                    "findings": [],
                    "strengths": [],
                    "evidenceReviewed": [],
                    "tracking": {"processId": 1, "startedAt": "t", "completedAt": "t2"},
                }
            )
            + "\n",
            encoding="utf-8",
        )

    # Move task to done and QA to done (bundle must be generated by real validate).
    run_edison(session_scenario_env, ["task", "status", task_id, "--status", "done", "--force"])
    run_edison(session_scenario_env, ["qa", "promote", task_id, "--status", "todo", "--session", sid])
    run_edison(session_scenario_env, ["qa", "promote", task_id, "--status", "wip", "--session", sid])
    run_edison(
        session_scenario_env,
        ["qa", "validate", task_id, "--session", sid, "--preset", "strict", "--check-only"],
    )
    run_edison(session_scenario_env, ["qa", "promote", task_id, "--status", "done", "--session", sid])

    # Session close verification requires session-close command evidence.
    run_edison(session_scenario_env, ["evidence", "init", task_id])
    run_edison(session_scenario_env, ["evidence", "capture", task_id, "--session-close"])

    # Close session: verification triggers restore to global + transition to closing (done dir)
    run_edison(session_scenario_env, ["session", "close", sid])

    closing_session_json = session_scenario_env["tmp"] / ".project" / "sessions" / "done" / sid / "session.json"
    assert closing_session_json.exists()

    # Records restored to global queues
    global_task = session_scenario_env["tmp"] / ".project" / "tasks" / "done" / f"{task_id}.md"
    assert global_task.exists()
    restored_session_task = session_scenario_env["tmp"] / ".project" / "sessions" / "done" / sid / "tasks" / "wip" / f"{task_id}.md"
    assert not restored_session_task.exists()


def test_scenario_02_timeout_reclaim(session_scenario_env: dict) -> None:
    """Timeout cleanup: expired session restored to global and moved to closing."""
    sid = "test-timeout"
    run_edison(
        session_scenario_env,
        ["session", "create", "--owner", "test-user", "--session-id", sid, "--mode", "start", "--no-worktree"],
    )

    run_edison(session_scenario_env, ["task", "new", "--id", "200", "--wave", "wave1", "--slug", "timeout"])
    task_id = "200-wave1-timeout"
    run_edison(session_scenario_env, ["task", "claim", task_id, "--session", sid])

    # Age session metadata (simulate inactivity beyond configured timeout)
    session_json = session_scenario_env["tmp"] / ".project" / "sessions" / "wip" / sid / "session.json"
    data = json.loads(session_json.read_text(encoding="utf-8"))
    old_time = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    meta = data.setdefault("meta", {})
    meta["createdAt"] = old_time
    meta["lastActive"] = old_time
    if "claimedAt" in meta:
        meta["claimedAt"] = old_time
    session_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_edison(session_scenario_env, ["session", "cleanup-expired", "--json"])
    payload = json.loads(res.stdout or "{}")
    cleaned = payload.get("cleaned") or []
    assert sid in cleaned

    closing_session_json = session_scenario_env["tmp"] / ".project" / "sessions" / "done" / sid / "session.json"
    assert closing_session_json.exists()
    global_task = session_scenario_env["tmp"] / ".project" / "tasks" / "wip" / f"{task_id}.md"
    assert global_task.exists()


def test_scenario_03_concurrent_claims(session_scenario_env: dict) -> None:
    """Concurrent claims: second session cannot claim an already-claimed task."""
    sid1 = "claim-a"
    sid2 = "claim-b"
    for sid in (sid1, sid2):
        run_edison(
            session_scenario_env,
            ["session", "create", "--owner", "test-user", "--session-id", sid, "--mode", "start", "--no-worktree"],
        )

    run_edison(session_scenario_env, ["task", "new", "--id", "300", "--wave", "wave1", "--slug", "concurrent"])
    task_id = "300-wave1-concurrent"

    run_edison(session_scenario_env, ["task", "claim", task_id, "--session", sid1])
    res = run_edison(session_scenario_env, ["task", "claim", task_id, "--session", sid2], check=False)
    assert res.returncode != 0

    s1_task = session_scenario_env["tmp"] / ".project" / "sessions" / "wip" / sid1 / "tasks" / "wip" / f"{task_id}.md"
    s2_task = session_scenario_env["tmp"] / ".project" / "sessions" / "wip" / sid2 / "tasks" / "wip" / f"{task_id}.md"
    assert s1_task.exists()
    assert not s2_task.exists()


def test_scenario_04_stuck_session_recovery(session_scenario_env: dict) -> None:
    """Recovery: `edison session recovery recover` transitions to recovery and can restore records."""
    sid = "test-recover"
    run_edison(
        session_scenario_env,
        ["session", "create", "--owner", "test-user", "--session-id", sid, "--mode", "start", "--no-worktree"],
    )

    run_edison(session_scenario_env, ["task", "new", "--id", "400", "--wave", "wave1", "--slug", "recover"])
    task_id = "400-wave1-recover"
    run_edison(session_scenario_env, ["task", "claim", task_id, "--session", sid])

    run_edison(session_scenario_env, ["session", "recovery", "recover", "--session", sid, "--restore-records"])

    recovery_session_json = session_scenario_env["tmp"] / ".project" / "sessions" / "recovery" / sid / "session.json"
    assert recovery_session_json.exists()
    global_task = session_scenario_env["tmp"] / ".project" / "tasks" / "wip" / f"{task_id}.md"
    assert global_task.exists()


def test_scenario_05_worktree_corruption(session_scenario_env: dict) -> None:
    """Worktree utilities: clean-worktrees runs in dry-run mode in a real git repo."""
    create_repo_with_git(session_scenario_env["tmp"])
    res = run_edison(session_scenario_env, ["session", "recovery", "clean-worktrees", "--dry-run", "--json"])
    payload = json.loads(res.stdout)
    assert payload.get("status") == "completed"


def test_scenario_06_local_session(session_scenario_env: dict) -> None:
    """Local session (no worktree): tracking commands work and remain deterministic."""
    sid = "test-local"
    run_edison(
        session_scenario_env,
        ["session", "create", "--owner", "test-user", "--session-id", sid, "--mode", "start", "--no-worktree"],
    )

    run_edison(session_scenario_env, ["task", "new", "--id", "500", "--wave", "wave1", "--slug", "local"])
    task_id = "500-wave1-local"
    run_edison(session_scenario_env, ["task", "claim", task_id, "--session", sid])

    started = run_edison(
        session_scenario_env,
        ["session", "track", "start", "--task", task_id, "--type", "implementation", "--model", "codex", "--json"],
    )
    start_payload = json.loads(started.stdout)
    assert start_payload.get("taskId") == task_id

    heartbeat = run_edison(session_scenario_env, ["session", "track", "heartbeat", "--task", task_id, "--json"])
    hb_payload = json.loads(heartbeat.stdout)
    assert isinstance(hb_payload.get("updated"), list)
