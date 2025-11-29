"""Test 08: TDD Workflow Enforcement (RED→GREEN→REFACTOR)

Covers Workstream 2 fixes:
 - HMAC tamper detection for evidence files
 - Coverage thresholds (90% overall / 100% changed) enforced at ready gate
 - Timestamp validation RED < GREEN < REFACTOR
 - `.only` detection blocks ready
 - REFACTOR step required or explicit waiver
 - Test discovery uses config patterns
 - Exit code checks for RED/GREEN/REFACTOR evidence logs
 - Test-before-implementation timing validated

Design notes:
- Uses the real `edison tasks ready` guard via run_script()
 - Creates minimal implementation-report.json in round-1
 - Provides local wrappers under `<tmp>/scripts/*` when required
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
)
from helpers.env import TestProjectDir, TestGitRepo, create_tdd_evidence


def _impl_report(task_id: str) -> dict:
    now = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    return {
        "taskId": task_id,
        "round": 1,
        "implementationApproach": "orchestrator-direct",
        "primaryModel": "codex",
        "completionStatus": "complete",
        "blockers": [],
        "followUpTasks": [],
        "tracking": {"processId": 1, "startedAt": now, "completedAt": now, "hostname": "e2e"},
        "tddCompliance": {"followed": True},
    }


def _ensure_ready_prereqs(project: TestProjectDir, task_id: str, session_id: str) -> Path:
    # Create QA brief and session + claim
    run_script("qa/new", [task_id], cwd=project.tmp_path)
    run_script(
        "session", ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"],
        cwd=project.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project.tmp_path)
    # Minimal implementation report and round-1 dir
    rd = project.project_root / "qa" / "validation-evidence" / task_id / "round-1"
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "implementation-report.json").write_text(json.dumps(_impl_report(task_id)))
    return rd


def _write_file(rd: Path, name: str, body: str) -> None:
    p = rd / name
    p.write_text(body)


def _sync_session_git_metadata(project: TestProjectDir, session_id: str, worktree_path: Path, base_branch: str = "main") -> None:
    """Ensure session JSON includes git worktree metadata in both layouts."""
    session_root = project.project_root / "sessions" / "wip"
    candidates = [
        session_root / session_id / "session.json",
        session_root / f"{session_id}.json",
    ]

    data = None
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text())
            break
    if data is None:
        data = {"sessionId": session_id, "state": "wip", "tasks": [], "qa": []}

    data.setdefault("git", {})
    data["git"]["worktreePath"] = str(worktree_path)
    data["git"]["baseBranch"] = base_branch

    for path in candidates:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))


@pytest.mark.fast
def test_only_detection_blocks_ready(project_dir: TestProjectDir):
    task_id = "808-w2-only-detect"
    session_id = "sess-only"
    run_script("tasks/new", ["--id", "808", "--wave", "w2", "--slug", "only-detect"], cwd=project_dir.tmp_path)
    rd = _ensure_ready_prereqs(project_dir, task_id, session_id)

    # Create a test file containing .only
    test_file = project_dir.tmp_path / "apps" / "example-app" / "src" / "sample.test.ts"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("describe.only('focus', () => { it('x', () => {}) })\n")

    # Create the 4 evidence files so the guard reaches .only detection
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        _write_file(rd, name, "RUNNER: tasks/ready\nSTART: now\nCMD: echo ok\nEXIT_CODE: 0\nEND\n")

    res = run_script("tasks/ready", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res)
    assert ".only" in (res.stderr + res.stdout)


@pytest.mark.fast
def test_coverage_script_enforced_at_ready(project_dir: TestProjectDir):
    task_id = "809-w2-coverage"
    session_id = "sess-coverage"
    run_script("tasks/new", ["--id", "809", "--wave", "w2", "--slug", "coverage"], cwd=project_dir.tmp_path)
    rd = _ensure_ready_prereqs(project_dir, task_id, session_id)

    # Provide the four required evidence files
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        _write_file(rd, name, "RUNNER: tasks/ready\nSTART: now\nCMD: echo ok\nEXIT_CODE: 0\nEND\n")

    # Add a local coverage verifier that fails (<90%) so ready must fail
    scripts_dir = project_dir.tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    verifier = scripts_dir / "tdd-verification.sh"
    verifier.write_text("""#!/usr/bin/env bash
echo "❌ FAIL: Overall line coverage 75% < 90%" 1>&2
exit 1
""")
    verifier.chmod(0o755)

    res = run_script("tasks/ready", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res)
    assert "coverage" in (res.stderr + res.stdout).lower()


@pytest.mark.fast
def test_hmac_tamper_detection(project_dir: TestProjectDir, monkeypatch):
    task_id = "810-w2-hmac"
    session_id = "sess-hmac"
    run_script("tasks/new", ["--id", "810", "--wave", "w2", "--slug", "hmac"], cwd=project_dir.tmp_path)
    rd = _ensure_ready_prereqs(project_dir, task_id, session_id)

    # Provide a strong but known HMAC key in env
    monkeypatch.setenv("project_EVIDENCE_HMAC_KEY", "test-secret-key-123")

    # Ask guard to generate evidence (so it writes signatures)
    _ = run_script("tasks/ready", [task_id, "--session", session_id, "--run"], cwd=project_dir.tmp_path)
    # Normalize all four evidence files to EXIT_CODE: 0 while keeping original signatures → triggers HMAC mismatch later
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        _write_file(rd, name, "RUNNER: tasks/ready\nSTART: now\nCMD: echo ok\nEXIT_CODE: 0\nEND\n")

    # Tamper with one evidence file; signature must fail specifically for HMAC
    tamper_file = rd / "command-lint.txt"
    tamper_file.write_text(tamper_file.read_text() + "tamper\n")

    res2 = run_script("tasks/ready", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res2)
    assert "HMAC" in (res2.stderr + res2.stdout)


@pytest.mark.requires_git
def test_tdd_commit_order_with_refactor_required(combined_env):
    project, git = combined_env
    task_id = "811-w2-tdd"
    session_id = "sess-tdd"

    # Prepare task and evidence skeleton
    run_script("tasks/new", ["--id", "811", "--wave", "w2", "--slug", "tdd"], cwd=project.tmp_path)
    rd = _ensure_ready_prereqs(project, task_id, session_id)
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        _write_file(rd, name, "RUNNER: tasks/ready\nSTART: now\nCMD: echo ok\nEXIT_CODE: 0\nEND\n")

    # Create a worktree and commit RED → GREEN (without REFACTOR) to force failure
    wt = git.create_worktree(session_id)
    # Add sample source and test files
    src = wt / "apps" / "example-app" / "src"
    test = src / "calc.test.ts"
    impl = src / "calc.ts"
    src.mkdir(parents=True, exist_ok=True)
    red_ts = time.time()
    test.write_text("it('adds', () => { expect(1+1).toBe(3) })\n")
    git.commit_in_worktree(wt, "[RED] failing test")
    test_commit = git.get_head_hash(wt)
    impl.write_text("export const add=(a:number,b:number)=>a+b\n")
    git.commit_in_worktree(wt, "[GREEN] make test pass")
    green_ts = red_ts + 5
    impl_commit = git.get_head_hash(wt)

    # Link session to worktree in both session layouts
    _sync_session_git_metadata(project, session_id, wt)

    # Provide TDD evidence (no refactor yet)
    create_tdd_evidence(
        project,
        session_id,
        task_id,
        test_commit=test_commit,
        impl_commit=impl_commit,
        red_ts=red_ts,
        green_ts=green_ts,
    )

    res = run_script("tasks/ready", [task_id, "--session", session_id], cwd=project.tmp_path)
    assert_command_failure(res)
    assert "REFACTOR" in (res.stderr + res.stdout)

    # Add REFACTOR commit and verify success
    refactor_ts = green_ts + 5
    (src / "calc.ts").write_text("export const add=(a:number,b:number)=>a+b // refactor\n")
    git.commit_in_worktree(wt, "[REFACTOR] cleanup")
    refactor_commit = git.get_head_hash(wt)

    create_tdd_evidence(
        project,
        session_id,
        task_id,
        test_commit=test_commit,
        impl_commit=impl_commit,
        refactor_commit=refactor_commit,
        red_ts=red_ts,
        green_ts=green_ts,
        refactor_ts=refactor_ts,
    )
    res2 = run_script("tasks/ready", [task_id, "--session", session_id], cwd=project.tmp_path)
    assert_command_success(res2)


@pytest.mark.requires_git
def test_tdd_red_green_timestamps_and_test_before_impl(combined_env):
    project, git = combined_env
    task_id = "812-w2-tdd-time"
    session_id = "sess-time"

    run_script("tasks/new", ["--id", "812", "--wave", "w2", "--slug", "tdd-time"], cwd=project.tmp_path)
    rd = _ensure_ready_prereqs(project, task_id, session_id)
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        _write_file(rd, name, "RUNNER: tasks/ready\nSTART: now\nCMD: echo ok\nEXIT_CODE: 0\nEND\n")

    wt = git.create_worktree(session_id)
    src = wt / "apps" / "example-app" / "src"
    testf = src / "timer.test.ts"
    implf = src / "timer.ts"
    src.mkdir(parents=True, exist_ok=True)
    red_ts = time.time()
    testf.write_text("it('fails', () => { expect(1+1).toBe(3) })\n")
    git.commit_in_worktree(wt, "[RED] failing test for timer")
    test_commit = git.get_head_hash(wt)
    implf.write_text("export const t=()=>2\n")
    git.commit_in_worktree(wt, "[GREEN] make timer pass")
    green_ts = red_ts + 5
    impl_commit = git.get_head_hash(wt)
    (src / "timer.ts").write_text("export const t=()=>2 // refactor\n")
    git.commit_in_worktree(wt, "[REFACTOR] cleanup timer")
    refactor_ts = green_ts + 5
    refactor_commit = git.get_head_hash(wt)

    # Link session to worktree in both layouts
    _sync_session_git_metadata(project, session_id, wt)

    # Provide TDD evidence with ordered timestamps
    create_tdd_evidence(
        project,
        session_id,
        task_id,
        test_commit=test_commit,
        impl_commit=impl_commit,
        refactor_commit=refactor_commit,
        red_ts=red_ts,
        green_ts=green_ts,
        refactor_ts=refactor_ts,
    )

    res = run_script("tasks/ready", [task_id, "--session", session_id], cwd=project.tmp_path)
    assert_command_success(res)
