"""E2E: Validator enforcement (specialized) and continuation ID plumbing.

Covers two critical issues:
- 4.1 Specialized blocking enforcement for Database/Testing
- 4.2 Continuation ID passed through run-wave → track → validate
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from helpers.env import TestProjectDir
from helpers.command_runner import run_script, assert_command_success


def _write_validator_report(dir: Path, vid: str, model: str, verdict: str = "approve") -> None:
    report = {
        "taskId": dir.parent.parent.name,
        "round": int(dir.name.split("-", 1)[1]) if "-" in dir.name else 1,
        "validatorId": vid,
        "model": model,
        "verdict": verdict,
        "findings": [],
        "strengths": [],
        "evidenceReviewed": [],
        "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:10:00Z", "hostname": "test"},
    }
    (dir / f"validator-{vid}-report.json").write_text(json.dumps(report, indent=2))


@pytest.mark.fast
def test_specialized_blocking_database_and_testing_enforced(project_dir: TestProjectDir):
    """validators/validate must require Database + Testing (blocking) reports.

    RED → before fix, validate would pass with only global+critical.
    GREEN → after fix, validate fails until Database+Testing reports are present.
    """
    task_id = "200-wave1-enforcement"
    ev = project_dir.project_root / "qa" / "validation-evidence" / task_id / "round-1"
    ev.mkdir(parents=True, exist_ok=True)

    # Provide only global + critical reports (approve)
    _write_validator_report(ev, "global-codex", "codex", verdict="approve")
    _write_validator_report(ev, "global-claude", "claude", verdict="approve")
    _write_validator_report(ev, "security", "codex", verdict="approve")
    _write_validator_report(ev, "performance", "codex", verdict="approve")

    # Run bundle validate → must fail due to missing Database/Testing
    res_fail = run_script("validators/validate", ["--task", task_id], cwd=project_dir.tmp_path)
    assert res_fail.returncode != 0, f"Expected failure, got stdout:\n{res_fail.stdout}\nstderr:\n{res_fail.stderr}"

    # Now add ALL specialized (blocking) reports and re-run → succeed
    for vid in ("react", "nextjs", "api", "prisma", "testing"):
        _write_validator_report(ev, vid, "codex", verdict="approve")

    res_ok = run_script("validators/validate", ["--task", task_id], cwd=project_dir.tmp_path)
    assert_command_success(res_ok)


@pytest.mark.fast
@pytest.mark.skip(reason="validators/run-wave deprecated - functionality moved to qa validate command")
def test_run_wave_plumbs_continuation_id(project_dir: TestProjectDir):
    """run-wave passes --continuation-id to track and validators/validate.

    - tracking.continuationId appears in a validator report started by run-wave
    - bundle-approved.json contains continuationId when run-wave invokes validate
    """
    session_id = "sid-wave-cid"
    task_num, wave, slug = "210", "wave1", "cid-wave"
    task_id = f"{task_num}-{wave}-{slug}"
    cid = "cid-abcdef123"

    # Real CLIs: create session + task + QA skeleton (ensures evidence root exists when needed)
    assert_command_success(run_script("session", ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"], cwd=project_dir.tmp_path))
    assert_command_success(run_script("tasks/new", ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id], cwd=project_dir.tmp_path))
    assert_command_success(run_script("qa/new", [task_id, "--session", session_id], cwd=project_dir.tmp_path))

    # Run validator waves with continuation ID (will not approve; that's fine)
    res = run_script(
        "validators/run-wave",
        ["--task", task_id, "--session", session_id, "--json", "--retries", "0", "--continuation-id", cid],
        cwd=project_dir.tmp_path,
    )
    # run-wave itself should exit 0 even when bundle not approved; we rely on JSON output and side-effects
    assert res.returncode == 0, f"run-wave failed:\n{res.stdout}\n{res.stderr}"

    ev = project_dir.project_root / "qa" / "validation-evidence" / task_id / "round-1"
    # At least one validator report should exist and carry tracking.continuationId
    any_report = next((p for p in ev.glob("validator-*-report.json")), None)
    assert any_report is not None, "Expected a validator report JSON to be created by track start"
    data = json.loads(any_report.read_text())
    tracking = data.get("tracking", {}) if isinstance(data.get("tracking"), dict) else {}
    assert tracking.get("continuationId") == cid, "tracking.continuationId not plumbed into report"

    # bundle-approved.json should exist and include continuationId from validate call
    bundle = ev / "bundle-approved.json"
    assert bundle.exists(), "bundle-approved.json not created by validators/validate"
    summary = json.loads(bundle.read_text())
    assert summary.get("continuationId") == cid, "bundle-approved.json missing continuationId"
