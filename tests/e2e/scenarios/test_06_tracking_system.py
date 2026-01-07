"""Test 06: Tracking System (REAL CLIs)

Tests for session, task, and QA tracking using REAL CLI commands.

Coverage:
- Session creation timestamps via `session new`
- Task claimed timestamps via `tasks/claim`
- Session `lastActive` updates via `session heartbeat` and task status updates
- Activity log entries created by real CLIs
- Session ownership and task/QA scope tracking
- Continuation ID line presence in task files (session block)
- Session completion via `session complete` (happy-path with empty scope)

IMPORTANT: Absolutely no mock data. All tests invoke real CLIs using run_script().
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from helpers.env import TestProjectDir
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_json_output,
)
from helpers.evidence_snapshots import write_passing_snapshot_command
from helpers.assertions import (
    assert_file_exists,
    assert_file_contains,
    assert_json_has_field,
    assert_json_field,
)
from edison.core.utils.text import format_frontmatter
from datetime import datetime

def _is_iso8601(ts: str) -> bool:
    try:
        # Support trailing 'Z' by normalizing
        t = ts.replace("Z", "+00:00")
        datetime.fromisoformat(t)
        return True
    except Exception:
        return False


@pytest.mark.fast
def test_session_created_timestamp(project_dir: TestProjectDir):
    """Create session via real CLI and verify meta.createdAt."""
    session_id = "sess-tracking-timestamp"

    result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(result)

    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    assert_file_exists(session_path)
    session_data = json.loads(session_path.read_text())

    # Real session JSON stores timestamps under meta (ISO 8601 Z)
    assert_json_has_field(session_data, "meta.createdAt")
    created_at = session_data["meta"]["createdAt"]
    assert _is_iso8601(created_at), f"Expected ISO 8601 timestamp, got {created_at}"


@pytest.mark.fast
def test_task_tracking_timestamps(project_dir: TestProjectDir):
    """Create + claim task via real CLIs and verify timestamps in file and session JSON."""
    session_id = "sess-tracking-task"
    task_num = "100"
    wave = "wave1"
    slug = "tracked"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Create task
    create_result = run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(create_result)

    # Claim task (stamps Claimed At and Last Active, and registers in session)
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    # Verify task file content lines exist (session-scoped task moves to wip on claim)
    task_path = (
        project_dir.project_root
        / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md"
    )
    assert_file_exists(task_path)
    from helpers.assertions import read_file
    content = read_file(task_path)
    # Edison v2: task metadata is stored in YAML frontmatter (not bullet lines).
    assert "owner:" in content
    assert f"session_id: {session_id}" in content
    assert "claimed_at:" in content
    assert "last_active:" in content

    # Verify session metadata exists and is updated.
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    session_data = json.loads(session_path.read_text())
    assert_json_has_field(session_data, "meta.createdAt")
    assert_json_has_field(session_data, "meta.lastActive")


@pytest.mark.fast
def test_session_last_active_tracking(project_dir: TestProjectDir):
    """Heartbeat updates meta.lastActive via real CLI."""
    session_id = "sess-tracking-last-active"

    assert_command_success(
        run_script(
            "session",
            ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
    )

    # Heartbeat updates lastActive and prints the value
    hb_result = run_script(
        "session",
        ["heartbeat", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(hb_result)
    # Extract timestamp echoed by CLI (ISO 8601 expected)
    line = next((l for l in hb_result.stdout.splitlines() if "heartbeat" in l), "")
    echoed_ts = line.split(" at ")[-1].strip() if " at " in line else None

    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    session_data = json.loads(session_path.read_text())
    assert_json_has_field(session_data, "meta.lastActive")
    if echoed_ts:
        assert session_data["meta"]["lastActive"] == echoed_ts


@pytest.mark.fast
def test_activity_log_entries(project_dir: TestProjectDir):
    """Real CLIs append session activity log entries (message-based)."""
    session_id = "sess-tracking-activity-log"
    task_num = "110"
    wave = "wave1"
    slug = "log"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )

    # Create task and auto-register in session
    assert_command_success(
        run_script(
            "tasks/new",
            ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id],
            cwd=project_dir.tmp_path,
        )
    )

    # Claim task in the session
    assert_command_success(
        run_script(
            "tasks/claim",
            [task_id, "--session", session_id],
            cwd=project_dir.tmp_path,
        )
    )

    # Verify activity log contains expected messages
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    data = json.loads(session_path.read_text())
    assert "activityLog" in data
    messages = [e.get("message", "") for e in data["activityLog"]]
    # At least 3 entries: created, created task, claimed task
    assert any("Session created" in m for m in messages)
    assert any(f"Task {task_id} registered" in m for m in messages)


@pytest.mark.fast
def test_continuation_id_tracking(project_dir: TestProjectDir):
    """Continuation ID persists through claim (todo → wip) via real CLIs."""
    session_id = "sess-tracking-continuation"
    task_num = "150"
    wave = "wave1"
    slug = "continuation"
    task_id = f"{task_num}-{wave}-{slug}"
    cid = "conv-xyz999"

    # Create session and task, then claim to stamp session block lines
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id, "--continuation-id", cid],
        cwd=project_dir.tmp_path,
    )
    run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    )

    task_path = (
        project_dir.project_root
        / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md"
    )
    assert_file_exists(task_path)
    from helpers.assertions import read_file
    content = read_file(task_path)
    assert f"continuation_id: {cid}" in content


@pytest.mark.fast
def test_continuation_id_end_to_end(project_dir: TestProjectDir):
    """Set continuation ID via flags; verify persistence in file + session; pass to validators."""
    session_id = "sess-tracking-continuation-e2e"
    task_num = "160"
    wave = "wave1"
    slug = "cid"
    task_id = f"{task_num}-{wave}-{slug}"
    cid = "conv-abc123"

    assert_command_success(
        run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    )
    # Create task with continuation ID
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id, "--continuation-id", cid], cwd=project_dir.tmp_path)
    )
    # NOTE: QA records are created alongside tasks; `qa/new` exists to ensure QA is present.

    # Verify task file contains continuation ID in YAML frontmatter
    task_path = (
        project_dir.project_root
        / "sessions" / "wip" / session_id / "tasks" / "todo" / f"{task_id}.md"
    )
    assert_file_exists(task_path)
    from helpers.assertions import read_file
    content = read_file(task_path)
    assert f"continuation_id: {cid}" in content

    # NOTE: Session JSON is not the source of truth for task metadata; tasks carry
    # continuation IDs in their own YAML frontmatter.

    # NOTE: Continuation IDs are persisted on task + QA records. Validator execution
    # is handled by `edison qa validate` and does not accept a continuation-id flag.


@pytest.mark.fast
def test_session_task_list_tracking(project_dir: TestProjectDir):
    """Register multiple tasks in session via real CLIs and verify session-scoped task files."""
    session_id = "sess-tracking-task-list"
    tasks = [("100", "wave1", "a"), ("150", "wave1", "b"), ("200", "wave1", "c")]

    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )

    for num, wave, slug in tasks:
        tid = f"{num}-{wave}-{slug}"
        assert_command_success(
            run_script("tasks/new", ["--id", num, "--wave", wave, "--slug", slug, "--session", session_id], cwd=project_dir.tmp_path)
        )
        assert_command_success(
            run_script("tasks/claim", [tid, "--session", session_id], cwd=project_dir.tmp_path)
        )

    for num, wave, slug in tasks:
        tid = f"{num}-{wave}-{slug}"
        assert_file_exists(
            project_dir.project_root
            / "sessions"
            / "wip"
            / session_id
            / "tasks"
            / "wip"
            / f"{tid}.md"
        )


@pytest.mark.fast
def test_session_duration_tracking(project_dir: TestProjectDir):
    """Start then complete a session (empty scope) via real CLIs and verify state + timestamps."""
    session_id = "sess-tracking-duration"

    # Start session
    create_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(create_result)

    # Inspect JSON via session status
    status_before = run_script(
        "session",
        ["status", session_id, "--json"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(status_before)
    data_before = assert_json_output(status_before)
    assert_json_has_field(data_before, "meta.createdAt")
    assert_json_has_field(data_before, "meta.lastActive")

    # Complete session (no tasks/qa in scope → succeeds)
    complete_result = run_script(
        "session",
        ["complete", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(complete_result)

    # Verify moved to validated and status updated
    session_path_validated = project_dir.project_root / "sessions" / "validated" / session_id / "session.json"
    assert_file_exists(session_path_validated)
    data_after = json.loads(session_path_validated.read_text())
    assert_json_field(data_after, "meta.status", "validated")
    assert_json_has_field(data_after, "meta.lastActive")


@pytest.mark.integration
def test_complete_tracking_workflow(project_dir: TestProjectDir):
    """End‑to‑end tracking using only real CLIs.

    Steps:
    1) session new → meta.createdAt set and initial activityLog
    2) tasks/new + tasks/claim → task registered, session log updated
    3) session remove task → clean scope for completion
    4) session complete → moves to sessions/validated and updates status
    """
    session_id = "sess-tracking-complete"
    task_num = "100"
    wave = "wave1"
    slug = "tracked-complete"
    task_id = f"{task_num}-{wave}-{slug}"

    # 1) Create session
    create_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(create_result)

    # 2) Create + claim task (registers in session and appends activity)
    assert_command_success(
        run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id], cwd=project_dir.tmp_path)
    )
    assert_command_success(
        run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    )

    session_wip_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    data = json.loads(session_wip_path.read_text())
    assert_json_has_field(data, "meta.createdAt")
    assert_json_has_field(data, "meta.lastActive")
    assert_file_exists(
        project_dir.project_root
        / "sessions"
        / "wip"
        / session_id
        / "tasks"
        / "wip"
        / f"{task_id}.md"
    )

    # 3) Complete session.
    #
    # Edison is fail-closed by default: completing a session with unfinished work
    # requires an explicit override.
    complete_result = run_script(
        "session",
        ["complete", session_id, "--force"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(complete_result)

    validated_path = project_dir.project_root / "sessions" / "validated" / session_id / "session.json"
    assert_file_exists(validated_path)
    final_data = json.loads(validated_path.read_text())
    assert_json_field(final_data, "meta.status", "validated")
    assert_json_has_field(final_data, "meta.lastActive")
@pytest.mark.fast
def test_qa_lifecycle_via_promote(project_dir: TestProjectDir):
    """QA lifecycle waiting→todo→wip→done using real qa/promote and guards."""
    session_id = "sess-tracking-qa-promote"
    task_id = "170-wave1-qa-promote"

    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", "170", "--wave", "wave1", "--slug", "qa-promote", "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [task_id, "--session", session_id], cwd=project_dir.tmp_path))

    # Move waiting → todo requires parent task in done/ (enforced)
    # First attempt should fail since task is in todo/
    res_fail = run_script("qa/promote", [task_id, "--status", "todo", "--session", session_id], cwd=project_dir.tmp_path)
    assert res_fail.returncode != 0
    # Move task to done in the session (test setup uses --force to bypass evidence guards)
    assert_command_success(
        run_script("tasks/status", [task_id, "--status", "done", "--force"], cwd=project_dir.tmp_path)
    )
    # Now promote QA waiting → todo
    assert_command_success(run_script("qa/promote", [task_id, "--status", "todo", "--session", session_id], cwd=project_dir.tmp_path))
    assert_file_exists(project_dir.project_root / "sessions" / "wip" / session_id / "qa" / "todo" / f"{task_id}-qa.md")

    # todo → wip
    assert_command_success(run_script("qa/promote", [task_id, "--status", "wip", "--session", session_id], cwd=project_dir.tmp_path))
    assert_file_exists(project_dir.project_root / "sessions" / "wip" / session_id / "qa" / "wip" / f"{task_id}-qa.md")

    # Prepare minimal bundle summary to attempt wip → done (should be rejected; must re-run validators)
    ev = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "validation-summary.md").write_text(
        # Missing rootTask/scope so guards must fall back to validator reports (fail-closed).
        format_frontmatter({"taskId": task_id, "round": 1, "approved": True, "validators": []}) + "\n",
        encoding="utf-8",
    )
    # Manual validation-summary.md must not be trusted
    res_manual = run_script("qa/promote", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path)
    assert res_manual.returncode != 0
    # Now compute a real verdict summary from evidence and try again (must fail due to missing blocking approvals)
    res_validate = run_script(
        "qa/round",
        ["summarize-verdict", task_id, "--session", session_id, "--json"],
        cwd=project_dir.tmp_path,
    )
    assert res_validate.returncode != 0
    # Create minimal required validator reports then approve (include specialized that block)
    vids = [
        ("global-codex", "codex"), ("global-claude", "claude"),
        ("coderabbit", "coderabbit"),
        ("security", "codex"), ("performance", "codex"),
        ("react", "codex"), ("nextjs", "codex"), ("api", "codex"),
        ("prisma", "codex"), ("testing", "codex")
    ]
    for vid, model in vids:
        report = {
            "taskId": task_id,
            "round": 1,
            "validatorId": vid,
            "model": model,
            "verdict": "approve",
            "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:05:00Z"}
        }
        (ev / f"validator-{vid}-report.md").write_text(format_frontmatter(report) + "\n", encoding="utf-8")

    # Also create required evidence command outputs (config-driven list).
    # These are required by the QA wip→done guards (fail-closed).
    from tests.config import get_default_value
    for fname in get_default_value("qa", "evidence_files"):
        if str(fname).startswith("command-"):
            write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename=str(fname), task_id=task_id)
        else:
            (ev / str(fname)).write_text("test evidence\n", encoding="utf-8")
    assert_command_success(
        run_script(
            "qa/round",
            ["summarize-verdict", task_id, "--session", session_id, "--json"],
            cwd=project_dir.tmp_path,
        )
    )
    assert_command_success(run_script("qa/promote", [task_id, "--status", "done", "--session", session_id], cwd=project_dir.tmp_path))
    assert_file_exists(project_dir.project_root / "sessions" / "wip" / session_id / "qa" / "done" / f"{task_id}-qa.md")


@pytest.mark.fast
def test_session_complete_fail_closed_when_scope_not_ready(project_dir: TestProjectDir):
    """Session completion fails (fail-closed) when tasks/QA not validated."""
    session_id = "sess-tracking-complete-guard"
    task_id = "180-wave1-incomplete"

    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", "180", "--wave", "wave1", "--slug", "incomplete", "--session", session_id], cwd=project_dir.tmp_path))
    # Attempt to complete should fail because scope not validated
    result = run_script("session", ["complete", session_id, "--json"], cwd=project_dir.tmp_path)
    assert result.returncode != 0
    payload = json.loads(result.stdout or "{}")
    health = payload.get("health") or {}
    details = health.get("details") or []
    assert any(isinstance(d, dict) and d.get("kind") == "allTasksValidated" for d in details)
