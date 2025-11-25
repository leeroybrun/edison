from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers.command_runner import run_script, assert_command_success, assert_command_failure, assert_error_contains
from helpers.assertions import assert_file_exists
from helpers.test_env import TestProjectDir


def _seed_min_impl_and_commands(ev_round: Path, task_id: str) -> None:
    ev_round.mkdir(parents=True, exist_ok=True)
    impl = {
        "taskId": task_id,
        "round": 1,
        "implementationApproach": "orchestrator-direct",
        "primaryModel": "codex",
        "completionStatus": "complete",
        "followUpTasks": [],
        "notesForValidator": "ok",
        "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:02:00Z"},
    }
    (ev_round / "implementation-report.json").write_text(json.dumps(impl))
    for name in ("command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"):
        (ev_round / name).write_text("ok\n")


@pytest.mark.fast
def test_specialized_validators_missing_block(test_project_dir: TestProjectDir):
    """Missing blocking specialized validator (prisma/testing) must fail validators/validate."""
    task = "701-wave1-db-change"

    sid = "test-specialized-blocking"
    test_project_dir.create_session(sid, state="wip")
    assert_command_success(run_script("tasks/new", ["--id", "701", "--wave", "wave1", "--slug", "db-change"], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [task], cwd=test_project_dir.tmp_path))
    # Not necessary to set to done for this validator-only test

    rd = test_project_dir.project_root / "qa" / "validation-evidence" / task / "round-1"
    _seed_min_impl_and_commands(rd, task)

    # Provide only global+critical reports (omit prisma/testing specialized)
    vids = [("codex-global", "codex"), ("claude-global", "claude"), ("security", "codex"), ("performance", "codex")]
    for vid, model in vids:
        data = {"taskId": task, "round": 1, "validatorId": vid, "model": model, "verdict": "approve", "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:03:00Z"}}
        (rd / f"validator-{vid}-report.json").write_text(json.dumps(data))

    res = run_script("validators/validate", ["--task", task], cwd=test_project_dir.tmp_path)
    # Expect failure because prisma/testing specialized (blocksOnFail=true) are missing
    assert_command_failure(res)


@pytest.mark.integration
def test_child_requires_parent_bundle_approval(test_project_dir: TestProjectDir):
    """Child QA cannot promote to done unless approved in the parent bundle."""
    sid = "test-child-gates"
    parent = "720-wave1-parent"
    child = "720.1-wave1-child"

    test_project_dir.create_session(sid, state="wip")
    assert_command_success(run_script("tasks/new", ["--id", "720", "--wave", "wave1", "--slug", "parent"], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", "720.1", "--wave", "wave1", "--slug", "child"], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("tasks/link", [parent, child, "--session", sid], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [parent], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [child], cwd=test_project_dir.tmp_path))
    # Directly prepare parent/child task files under tasks/done/ to satisfy QA waiting→todo guard
    for tid in (child, parent):
        todo_path = test_project_dir.project_root / "tasks" / "todo" / f"{tid}.md"
        done_path = test_project_dir.project_root / "tasks" / "done" / f"{tid}.md"
        done_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join([
            f"# Task {tid}",
            "", 
            "- **Owner:** _unassigned_",
            "- **Status:** done",
            "- **Created:** 2025-01-01T00:00:00Z",
        ]) + "\n"
        done_path.write_text(content)
        try:
            todo_path.unlink()
        except FileNotFoundError:
            pass
    # tasks/status step no longer needed; files are already under tasks/done/

    # Seed child evidence with all blocking reports (but without parent bundle)
    child_rd = test_project_dir.project_root / "qa" / "validation-evidence" / child / "round-1"
    _seed_min_impl_and_commands(child_rd, child)
    for vid, model in [("codex-global", "codex"), ("claude-global", "claude"), ("security", "codex"), ("performance", "codex"), ("prisma", "codex"), ("testing", "codex")]:
        data = {"taskId": child, "round": 1, "validatorId": vid, "model": model, "verdict": "approve", "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:03:00Z"}}
        (child_rd / f"validator-{vid}-report.json").write_text(json.dumps(data))

    # Attempt to promote child without parent bundle approval → should fail
    res_child_done = run_script("qa/promote", ["--task", child, "--to", "done", "--session", sid], cwd=test_project_dir.tmp_path)
    assert_command_failure(res_child_done)

    # Now create minimal parent bundle approved including the child
    parent_rd = test_project_dir.project_root / "qa" / "validation-evidence" / parent / "round-1"
    _seed_min_impl_and_commands(parent_rd, parent)
    # Parent also gets fake blocking reports to allow validators/validate to proceed
    for vid, model in [("codex-global", "codex"), ("claude-global", "claude"), ("security", "codex"), ("performance", "codex"), ("prisma", "codex"), ("testing", "codex")]:
        data = {"taskId": parent, "round": 1, "validatorId": vid, "model": model, "verdict": "approve", "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:03:00Z"}}
        (parent_rd / f"validator-{vid}-report.json").write_text(json.dumps(data))

    # Optional: Parent bundle validation would enable child promotion once approved (covered by other E2E tests)


@pytest.mark.fast
def test_atomic_rollback_on_failed_done_promotion(test_project_dir: TestProjectDir):
    """If validators fail, qa/promote must not persist status or move the file."""
    sid = "test-atomic-rollback"
    task = "730-wave1-atomic"

    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", sid, "--mode", "start"], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", "730", "--wave", "wave1", "--slug", "atomic"], cwd=test_project_dir.tmp_path))
    # Directly place task under tasks/done/
    todo_path = test_project_dir.project_root / "tasks" / "todo" / f"{task}.md"
    done_path = test_project_dir.project_root / "tasks" / "done" / f"{task}.md"
    done_path.parent.mkdir(parents=True, exist_ok=True)
    done_path.write_text("\n".join([f"# Task {task}", "", "- **Owner:** _unassigned_", "- **Status:** done"]) + "\n")
    try:
        todo_path.unlink()
    except FileNotFoundError:
        pass
    # Seed a session-scoped QA file already in wip state
    qa_wip = test_project_dir.project_root / "sessions" / "wip" / sid / "qa" / "wip"
    qa_wip.mkdir(parents=True, exist_ok=True)
    qa_file = qa_wip / f"{task}-qa.md"
    qa_file.write_text("\n".join([f"# QA for {task}", "", "- **Validator Owner:** _unassigned_", "- **Status:** wip"]) + "\n")

    # Do NOT create evidence; validators/validate will fail
    res = run_script("qa/promote", ["--task", task, "--to", "done", "--session", sid], cwd=test_project_dir.tmp_path)
    assert_command_failure(res)

    # Ensure file is still in wip and status line still wip
    qa_path = test_project_dir.project_root / "sessions" / "wip" / sid / "qa" / "wip" / f"{task}-qa.md"
    assert_file_exists(qa_path)
    text = qa_path.read_text()
    assert "- **Status:** wip" in text


@pytest.mark.fast
def test_manual_file_move_bypass_rejected(test_project_dir: TestProjectDir):
    """Manually moving QA file between directories should be detected and rejected."""
    sid = "test-manual-move"
    task = "740-wave1-manual"

    test_project_dir.create_session(sid, state="wip")
    assert_command_success(run_script("tasks/new", ["--id", "740", "--wave", "wave1", "--slug", "manual"], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [task, "--session", sid], cwd=test_project_dir.tmp_path))
    # Manually move waiting→done (bypass)
    # Locate session-scoped waiting QA and move it to global done (manual bypass)
    src = test_project_dir.project_root / "sessions" / "wip" / sid / "qa" / "waiting" / f"{task}-qa.md"
    dst = test_project_dir.project_root / "qa" / "done" / f"{task}-qa.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text())
    src.unlink()

    # Any promote attempt should be rejected due to integrity mismatch
    res = run_script("qa/promote", ["--task", task, "--to", "validated", "--session", sid], cwd=test_project_dir.tmp_path)
    assert_command_failure(res)
    assert_error_contains(res, "Manual move detected")


@pytest.mark.fast
def test_tracking_stamps_required_for_approval(test_project_dir: TestProjectDir):
    """validators/validate should fail if tracking.completedAt is missing in reports."""
    task = "750-wave1-tracking"

    assert_command_success(run_script("tasks/new", ["--id", "750", "--wave", "wave1", "--slug", "tracking"], cwd=test_project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [task], cwd=test_project_dir.tmp_path))

    rd = test_project_dir.project_root / "qa" / "validation-evidence" / task / "round-1"
    _seed_min_impl_and_commands(rd, task)
    # Missing completedAt
    vids = [("codex-global", "codex"), ("claude-global", "claude"), ("security", "codex"), ("performance", "codex"), ("prisma", "codex"), ("testing", "codex")]
    for vid, model in vids:
        report = {"taskId": task, "round": 1, "validatorId": vid, "model": model, "verdict": "approve", "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z"}}
        (rd / f"validator-{vid}-report.json").write_text(json.dumps(report))
    res = run_script("validators/validate", ["--task", task], cwd=test_project_dir.tmp_path)
    assert_command_failure(res)
