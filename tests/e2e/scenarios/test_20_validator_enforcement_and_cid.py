"""E2E: Validator enforcement (specialized) and continuation ID plumbing.

Covers two critical issues:
- 4.1 Specialized blocking enforcement for Database/Testing
- 4.2 Continuation ID passed through run-wave → track → validate
"""
from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from helpers.env import TestProjectDir
from helpers.command_runner import run_script, assert_command_success
from edison.core.utils.text import format_frontmatter, parse_frontmatter


def _write_validator_report(dir: Path, vid: str, model: str, verdict: str = "approve") -> None:
    report = {
        # dir = .../.project/qa/validation-reports/<taskId>/round-N
        "taskId": dir.parent.name,
        "round": int(dir.name.split("-", 1)[1]) if "-" in dir.name else 1,
        "validatorId": vid,
        "model": model,
        "verdict": verdict,
        "findings": [],
        "strengths": [],
        "evidenceReviewed": [],
        "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00Z", "completedAt": "2025-01-01T00:10:00Z", "hostname": "test"},
    }
    (dir / f"validator-{vid}-report.md").write_text(
        format_frontmatter(report) + "\n# Validator Report\n",
        encoding="utf-8",
    )


@pytest.mark.fast
def test_specialized_blocking_database_and_testing_enforced(project_dir: TestProjectDir):
    """validators/validate must fail-closed until all blocking reports exist.

    This test is intentionally trigger-agnostic: we validate that *blocking*
    validators (as determined by the registry/roster) gate bundle approval.
    """
    task_id = "200-wave1-enforcement"
    cfg_dir = project_dir.tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(
        yaml.safe_dump(
            {
                "validation": {
                    "defaultPreset": "strict",
                    "evidence": {"requiredFiles": []},
                    "presets": {
                        "strict": {
                            "name": "strict",
                            "validators": ["v1", "v2", "v3", "v4"],
                            "blocking_validators": ["v1", "v2", "v3", "v4"],
                            "required_evidence": [],
                        }
                    },
                    "validators": {
                        # Disable bundled always-run validators to keep the roster deterministic.
                        "global-codex": {"enabled": False},
                        "global-claude": {"enabled": False},
                        "v1": {
                            "name": "V1",
                            "engine": "codex-cli",
                            "fallback_engine": "pal-mcp",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                        "v2": {
                            "name": "V2",
                            "engine": "codex-cli",
                            "fallback_engine": "pal-mcp",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                        "v3": {
                            "name": "V3",
                            "engine": "codex-cli",
                            "fallback_engine": "pal-mcp",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                        "v4": {
                            "name": "V4",
                            "engine": "codex-cli",
                            "fallback_engine": "pal-mcp",
                            "wave": "critical",
                            "always_run": False,
                            "blocking": True,
                            "triggers": [],
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    ev = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    ev.mkdir(parents=True, exist_ok=True)

    # Provide only a subset of blocking reports (approve)
    _write_validator_report(ev, "v1", "codex", verdict="approve")
    _write_validator_report(ev, "v2", "claude", verdict="approve")

    # Compute approval from existing evidence (no validator execution) → must fail due to
    # missing blocking approvals (e.g. security/performance).
    res_fail = run_script(
        "qa/round",
        ["summarize-verdict", task_id, "--preset", "strict", "--json"],
        cwd=project_dir.tmp_path,
    )
    assert res_fail.returncode != 0, f"Expected failure, got stdout:\n{res_fail.stdout}\nstderr:\n{res_fail.stderr}"

    # Now add the remaining core blocking reports and re-run → succeed
    _write_validator_report(ev, "v3", "codex", verdict="approve")
    _write_validator_report(ev, "v4", "codex", verdict="approve")

    res_ok = run_script(
        "qa/round",
        ["summarize-verdict", task_id, "--preset", "strict", "--json"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(res_ok)


@pytest.mark.fast
@pytest.mark.skip(reason="validators/run-wave deprecated - functionality moved to qa validate command")
def test_run_wave_plumbs_continuation_id(project_dir: TestProjectDir):
    """run-wave passes --continuation-id to track and validators/validate.

    - tracking.continuationId appears in a validator report started by run-wave
    - validation-summary.md contains continuationId when run-wave invokes validate
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

    ev = project_dir.project_root / "qa" / "validation-reports" / task_id / "round-1"
    # At least one validator report should exist and carry tracking.continuationId
    any_report = next((p for p in ev.glob("validator-*-report.md")), None)
    assert any_report is not None, "Expected a validator report to be created by track start"
    data = parse_frontmatter(any_report.read_text()).frontmatter
    tracking = data.get("tracking", {}) if isinstance(data.get("tracking"), dict) else {}
    assert tracking.get("continuationId") == cid, "tracking.continuationId not plumbed into report"

    # validation-summary.md should exist and include continuationId from validate call
    bundle = ev / "validation-summary.md"
    assert bundle.exists(), "validation-summary.md not created by validators/validate"
    summary = parse_frontmatter(bundle.read_text()).frontmatter
    assert summary.get("continuationId") == cid, "validation-summary.md missing continuationId"
