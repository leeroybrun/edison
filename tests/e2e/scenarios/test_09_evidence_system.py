"""Test 09: Evidence System (REAL CLI)

Refactored to use REAL CLI commands and the guarded workflow.

Coverage:
- Evidence directory structure via real task + QA creation
- Required evidence checked by `task done` guard
- Implementation report frontmatter validated by real validator wrapper
- Multi‑round evidence behavior
- Evidence completeness failure → success after creating files
- Command evidence stored as repo-state snapshots (not per-round files)
- Partial evidence scenario (guard should fail)
- End‑to‑end: wip → done guarded by evidence
"""
from __future__ import annotations

import pytest
from pathlib import Path

from helpers import TestProjectDir
from helpers.assertions import (
    assert_file_exists,
    assert_file_contains,
    assert_directory_exists,
)
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_output_contains,
)
from helpers.evidence_snapshots import write_passing_snapshot_command
from edison.core.utils.text import format_frontmatter, parse_frontmatter


# --- Local helpers for this test module ---
def _ensure_guard_wrappers(tmp_root: Path, repo_root: Path) -> None:
    """Create minimal wrappers under `<tmp>/scripts/*` that real guards expect.

    tasks/ready invokes top‑level scripts under `scripts/` in the current
    AGENTS_PROJECT_ROOT. Our test environment only calls edison CLI commands in the
    repository. These wrappers bridge the paths without mocking data.
    """
    scripts_dir = tmp_root / "scripts"
    (scripts_dir / "implementation").mkdir(parents=True, exist_ok=True)
    (scripts_dir / "tasks").mkdir(parents=True, exist_ok=True)

    impl_validate = scripts_dir / "implementation" / "validate"
    impl_validate.write_text(
        "#!/usr/bin/env bash\nedison validate \"$@\"\n"
    )
    impl_validate.chmod(0o755)

    ensure_followups = scripts_dir / "tasks" / "ensure-followups"
    ensure_followups.write_text(
        "#!/usr/bin/env bash\nedison task ensure_followups \"$@\"\n"
    )
    ensure_followups.chmod(0o755)


def _impl_report_json(task_id: str) -> dict:
    """Minimal schema‑compliant implementation report content."""
    import os, datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    return {
        "taskId": task_id,
        "round": 1,
        "implementationApproach": "orchestrator-direct",
        "primaryModel": "claude",
        "completionStatus": "complete",
        "blockers": [],
        "followUpTasks": [],
        "notesForValidator": "All checks green for demo",
        "tracking": {
            "processId": os.getpid(),
            "startedAt": now,
            "completedAt": now,
            "hostname": "e2e-local",
        },
    }


def _write_impl_report(round_dir: Path, payload: dict) -> None:
    (round_dir / "implementation-report.md").write_text(
        format_frontmatter(payload) + "\n# Implementation Report\n",
        encoding="utf-8",
    )


@pytest.mark.fast
def test_evidence_directory_structure(project_dir: TestProjectDir):
    """Creates a real task + QA, then ensures round-1 directory exists."""
    task_num, wave, slug = "100", "wave1", "evidence-structure"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create task and QA via REAL CLIs
    result = run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    assert_command_success(result)
    qa_res = run_script("qa/new", [task_id], cwd=project_dir.tmp_path)
    assert_command_success(qa_res)

    # Create minimal implementation report to materialize round-1 dir
    round_dir = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    _write_impl_report(round_dir, _impl_report_json(task_id))

    # Verify structure
    expected_path = round_dir
    assert_directory_exists(expected_path)


@pytest.mark.fast
def test_evidence_required_files(project_dir: TestProjectDir):
    """Guard checks for required command evidence in the snapshot store."""
    task_num, wave, slug = "150", "wave1", "required"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-evidence-required"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    # Create a session and claim the task before invoking tasks/ready
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)

    # Minimal implementation report (guard requires it)
    round_dir = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    _write_impl_report(round_dir, _impl_report_json(task_id))

    # Initially missing → done should fail
    done = run_script("tasks/done", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(done)
    assert "Missing/invalid command evidence" in (done.stderr + done.stdout)

    # Create required command evidence files in the snapshot store (schema-compliant).
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename=name, task_id=task_id)

    # Now guard should pass (after we provide implementation validator wrapper and followups wrapper)
    _ensure_guard_wrappers(project_dir.tmp_path, project_dir.project_root)
    done2 = run_script("tasks/done", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_success(done2)


@pytest.mark.fast
def test_evidence_file_content(project_dir: TestProjectDir):
    """Ensure each command evidence contains recognizable content."""
    task_num, wave, slug = "200", "wave1", "content"
    task_id = f"{task_num}-{wave}-{slug}"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    round_dir = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    _write_impl_report(round_dir, _impl_report_json(task_id))

    type_check_file = write_passing_snapshot_command(
        repo_root=project_dir.tmp_path,
        filename="command-type-check.txt",
        task_id=task_id,
        output="TypeScript: OK\n",
    )
    assert_file_exists(type_check_file)
    assert_file_contains(type_check_file, "evidenceKind: command")
    assert_file_contains(type_check_file, "exitCode: 0")


@pytest.mark.fast
def test_evidence_implementation_report(project_dir: TestProjectDir):
    """Implementation report is mandatory and validated by wrapper."""
    task_num, wave, slug = "250", "wave1", "impl-report"
    task_id = f"{task_num}-{wave}-{slug}"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    round_dir = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)

    # Write schema‑compliant report and validate with real validator via wrapper
    impl_report = round_dir / "implementation-report.md"
    _write_impl_report(round_dir, _impl_report_json(task_id))

    _ensure_guard_wrappers(project_dir.tmp_path, project_dir.project_root)
    # Invoke validator exactly how tasks/ready expects to
    validate_result = project_dir.run_command([
        str(project_dir.tmp_path / "scripts" / "implementation" / "validate"),
        str(impl_report),
    ], cwd=project_dir.tmp_path)
    assert_command_success(validate_result)
    assert_output_contains(validate_result, "Implementation report valid")


@pytest.mark.fast
def test_evidence_multiple_rounds(project_dir: TestProjectDir):
    """Round-1..3 directories exist and carry independent report artifacts."""
    task_num, wave, slug = "300", "wave1", "multi-round"
    task_id = f"{task_num}-{wave}-{slug}"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    for rn in (1, 2, 3):
        rd = project_dir.project_root / "qa" / "validation-reports" / task_id / f"round-{rn}"
        rd.mkdir(parents=True, exist_ok=True)
        _write_impl_report(rd, _impl_report_json(task_id) | {"round": rn})
        (rd / "round-notes.txt").write_text(f"round={rn}\n", encoding="utf-8")

    for rn in (1, 2, 3):
        round_dir = project_dir.project_root / "qa" / "validation-reports" / task_id / f"round-{rn}"
        assert_directory_exists(round_dir)
        assert_file_exists(round_dir / "implementation-report.md")
        assert_file_exists(round_dir / "round-notes.txt")


@pytest.mark.fast
def test_evidence_completeness_check(project_dir: TestProjectDir):
    """Guard fails without 4 command files, passes after adding them."""
    task_num, wave, slug = "350", "wave1", "completeness"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-evidence-completeness"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    _ensure_guard_wrappers(project_dir.tmp_path, project_dir.project_root)

    # Create a session and claim the task before invoking tasks/ready
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)

    rd = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    rd.mkdir(parents=True, exist_ok=True)
    _write_impl_report(rd, _impl_report_json(task_id))

    # No command evidence yet → done should fail
    r1 = run_script("tasks/done", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(r1)

    # Add all required files (snapshot store)
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename=name, task_id=task_id)

    r2 = run_script("tasks/done", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_success(r2)


@pytest.mark.fast
def test_evidence_git_diff_capture(project_dir: TestProjectDir):
    """Store a git diff snippet under round-1 for auditor reference."""
    task_num, wave, slug = "400", "wave1", "git-diff"
    task_id = f"{task_num}-{wave}-{slug}"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    rd = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    rd.mkdir(parents=True, exist_ok=True)
    _write_impl_report(rd, _impl_report_json(task_id))

    git_diff_file = rd / "git-diff.txt"
    git_diff_file.write_text(
        """diff --git a/src/auth.ts b/src/auth.ts
index abc123..def456 100644
--- a/src/auth.ts
+++ b/src/auth.ts
@@ -1,3 +1,5 @@
+import { z } from "zod";
+
 export const authenticate = (token: string) => {
   return validateToken(token);
 };
"""
    )

    assert_file_exists(git_diff_file)
    assert_file_contains(git_diff_file, "diff --git")
    assert_file_contains(git_diff_file, "src/auth.ts")


@pytest.mark.edge_case
def test_evidence_partial_files(project_dir: TestProjectDir):
    """Partial evidence present → guard should flag missing files."""
    task_num, wave, slug = "450", "wave1", "partial"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-evidence-partial"

    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)

    _ensure_guard_wrappers(project_dir.tmp_path, project_dir.project_root)

    # Create a session and claim the task before invoking tasks/ready
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)

    rd = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    rd.mkdir(parents=True, exist_ok=True)
    _write_impl_report(rd, _impl_report_json(task_id))
    # Only two of the four (snapshot store)
    write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename="command-type-check.txt", task_id=task_id)
    write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename="command-lint.txt", task_id=task_id)

    # Guard should fail and list missing files
    res = run_script("tasks/done", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_failure(res)
    assert "Missing/invalid command evidence" in (res.stderr + res.stdout)

    # In real workflow: edison tasks ready would FAIL (missing required files)


@pytest.mark.integration
@pytest.mark.slow
def test_evidence_complete_workflow(project_dir: TestProjectDir):
    """End‑to‑end: done transition is guarded by evidence (real CLIs)."""
    task_num, wave, slug = "500", "wave1", "evidence-complete"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-evidence-workflow"

    # Session + task + QA
    session_result = run_script("session", ["new", "--owner", "tester", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path)
    assert_command_success(session_result)
    task_result = run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug, "--owner", "tester", "--session", session_id], cwd=project_dir.tmp_path)
    assert_command_success(task_result)
    # Ensure the task is explicitly claimed for the active session
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)
    qa_result = run_script("qa/new", [task_id, "--owner", "validator"], cwd=project_dir.tmp_path)
    assert_command_success(qa_result)

    # Move to wip (allowed without evidence)
    wip_result = run_script("tasks/status", [task_id, "--status", "wip"], cwd=project_dir.tmp_path)
    assert_command_success(wip_result)

    # Try to move to done WITHOUT evidence → must fail (guard)
    _ensure_guard_wrappers(project_dir.tmp_path, project_dir.project_root)
    fail_done = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
        env={"ENFORCE_TASK_STATUS_EVIDENCE": "1"},
    )
    assert_command_failure(fail_done)

    # Round 1 evidence (implementation report + 4 command files)
    r1 = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    r1.mkdir(parents=True, exist_ok=True)
    # Add a primary file path to trigger Context7 for React
    task_md = project_dir.project_root / "tasks" / "wip" / f"{task_id}.md"
    if task_md.exists():
        txt = task_md.read_text()
        txt = txt.replace("**Primary Files / Areas:** (list paths)", "**Primary Files / Areas:** apps/example-app/src/components/App.tsx")
        task_md.write_text(txt)
    # Provide Context7 evidence to satisfy enforcement
    (r1 / "context7-react.txt").write_text("Context7 refreshed: react\n")
    _write_impl_report(r1, _impl_report_json(task_id))
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename=name, task_id=task_id)

    # Now the done move should succeed
    done_result = run_script(
        "tasks/status",
        [task_id, "--status", "done", "--session", session_id],
        cwd=project_dir.tmp_path,
        env={"ENFORCE_TASK_STATUS_EVIDENCE": "1"},
    )
    assert_command_success(done_result)
    assert_output_contains(done_result, "Status")

    # Round 2 (regression) still allowed and preserved
    r2 = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-2"
    r2.mkdir(parents=True, exist_ok=True)
    _write_impl_report(r2, _impl_report_json(task_id) | {"round": 2})
    (r2 / "round-notes.txt").write_text("round=2\n", encoding="utf-8")

    assert_directory_exists(r1)
    assert_directory_exists(r2)


@pytest.mark.fast
def test_validator_bundle_approval(project_dir: TestProjectDir):
    """Validator bundle validation with REAL CLI - all validators approve."""
    task_num, wave, slug = "550", "wave1", "validator-bundle"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-validator-bundle"

    # Create task, QA, session
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)

    # Setup evidence directory with implementation report and required files
    rd = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    rd.mkdir(parents=True, exist_ok=True)
    _write_impl_report(rd, _impl_report_json(task_id))
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename=name, task_id=task_id)

    # Create REAL validator report JSON files for all blocking validators
    # (global, critical, specialized from config)
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"

    for validator_id, model in [
        ("global-codex", "codex"),
        ("global-claude", "claude"),
        ("security", "codex"),
        ("performance", "codex"),
        ("prisma", "codex"),
        ("testing", "codex"),
    ]:
        validator_report = {
            "taskId": task_id,
            "round": 1,
            "validatorId": validator_id,
            "model": model,
            "verdict": "approve",
            "summary": f"All checks passed for {validator_id}",
            "findings": [],
            "followUpTasks": [],
            "tracking": {
                "processId": __import__("os").getpid(),
                "startedAt": now,
                "completedAt": now,
                "hostname": "e2e-test"
            }
        }
        (rd / f"validator-{validator_id}-report.md").write_text(
            format_frontmatter(validator_report) + "\n# Validator Report\n",
            encoding="utf-8",
        )

    summarize = run_script(
        "qa/round",
        ["summarize-verdict", task_id, "--session", session_id, "--json"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(summarize)

    # Verify validation-summary.md was created
    bundle_file = rd / "validation-summary.md"
    assert_file_exists(bundle_file)

    # Verify bundle structure matches REAL CLI output
    bundle_data = parse_frontmatter(bundle_file.read_text()).frontmatter
    assert bundle_data["taskId"] == task_id
    assert bundle_data["round"] == 1
    assert bundle_data["approved"] is True
    assert "missing" in bundle_data
    assert bundle_data["missing"] == []


@pytest.mark.fast
def test_validator_bundle_one_blocking_fails(project_dir: TestProjectDir):
    """REAL CLI consensus test: one blocking validator fails → approved: false."""
    task_num, wave, slug = "560", "wave1", "one-blocking-fails"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-one-blocking-fails"

    # Create task, QA, session
    run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug], cwd=project_dir.tmp_path)
    run_script("qa/new", [task_id], cwd=project_dir.tmp_path)
    run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    run_script("tasks/claim", [task_id, "--session", session_id], cwd=project_dir.tmp_path)

    # Setup evidence directory
    rd = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    rd.mkdir(parents=True, exist_ok=True)
    _write_impl_report(rd, _impl_report_json(task_id))
    for name in ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]:
        write_passing_snapshot_command(repo_root=project_dir.tmp_path, filename=name, task_id=task_id)

    # Create validator reports: 5 approve, 1 rejects (security fails)
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"

    for validator_id, model, verdict in [
        ("global-codex", "codex", "approve"),
        ("global-claude", "claude", "approve"),
        ("security", "codex", "reject"),  # BLOCKING VALIDATOR FAILS
        ("performance", "codex", "approve"),
        ("prisma", "codex", "approve"),
        ("testing", "codex", "approve"),
    ]:
        validator_report = {
            "taskId": task_id,
            "round": 1,
            "validatorId": validator_id,
            "model": model,
            "verdict": verdict,
            "summary": f"Security issues found" if verdict == "reject" else f"All checks passed for {validator_id}",
            "findings": [{"severity": "critical", "description": "SQL injection risk"}] if verdict == "reject" else [],
            "followUpTasks": [],
            "tracking": {
                "processId": __import__("os").getpid(),
                "startedAt": now,
                "completedAt": now,
                "hostname": "e2e-test"
            }
        }
        (rd / f"validator-{validator_id}-report.md").write_text(
            format_frontmatter(validator_report) + "\n# Validator Report\n",
            encoding="utf-8",
        )

    summarize = run_script(
        "qa/round",
        ["summarize-verdict", task_id, "--session", session_id, "--json"],
        cwd=project_dir.tmp_path,
    )
    assert_command_failure(summarize)  # Should fail because security rejected

    # Verify validation-summary.md shows approved: false
    bundle_file = rd / "validation-summary.md"
    assert_file_exists(bundle_file)
    bundle_data = parse_frontmatter(bundle_file.read_text()).frontmatter
    assert bundle_data["taskId"] == task_id
    assert bundle_data["approved"] is False  # One blocking validator failed
