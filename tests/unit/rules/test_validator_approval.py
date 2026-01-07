"""Tests for validator-approval rule checker."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from edison.core.rules import RulesEngine, RuleViolationError
from tests.helpers import format_round_dir, create_round_dir
from tests.helpers.env_setup import setup_project_root
from edison.core.utils.text import format_frontmatter


def _create_config(require: bool = True, max_age_days: int = 7) -> dict:
    return {
        "rules": {
            "byState": {
                "validated": [
                    {
                        "id": "validator-approval",
                        "description": "Must have validator approvals",
                        "enforced": True,
                        "blocking": True,
                        "config": {
                            "requireReport": require,
                            "maxAgeDays": max_age_days,
                        },
                    }
                ]
            }
        }
    }


def _bundle_filename(project_root: Path) -> str:
    from edison.core.qa.evidence.service import EvidenceService

    return EvidenceService("dummy", project_root=project_root).bundle_filename


def _evidence_base(project_root: Path) -> Path:
    return project_root / ".project" / "qa" / "validation-reports"


def _report_path(project_root: Path, task_id: str, round_no: int = 1) -> Path:
    return (
        _evidence_base(project_root)
        / task_id
        / format_round_dir(round_no)
        / _bundle_filename(project_root)
    ).resolve()


def _write_bundle(path: Path, payload: dict | None = None, *, approved: bool = True) -> None:
    """Helper to write a bundle approval file."""
    data = dict(payload or {})
    # approved flag always wins if explicitly passed
    data.setdefault("approved", bool(approved))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_frontmatter(data) + "\n# Bundle Approval\n", encoding="utf-8")


def test_validator_approval_passes_with_explicit_recent_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Explicit reportPath with approved=true should allow transition."""
    task_id = "VAL-001"
    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)
    rpt = _report_path(tmp_path, task_id)
    _write_bundle(rpt, approved=True)
    task = {"id": task_id, "validation": {"reportPath": str(rpt)}}

    engine = RulesEngine(_create_config())

    assert engine.check_state_transition(task, "done", "validated") == []


def test_validator_approval_blocks_when_missing_evidence_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No evidence dir → blocking RuleViolationError mentioning 'no evidence'."""
    task_id = "VAL-NO-EVIDENCE"

    # Isolated fake project root with no .project/qa tree
    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, "done", "validated")

    msg = str(exc.value).lower()
    assert "no evidence" in msg


def test_validator_approval_blocks_when_no_bundle_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Evidence round exists but bundle summary missing → blocks with clear message."""
    task_id = "VAL-NO-BUNDLE"

    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)

    base = tmp_path / ".project" / "qa" / "validation-reports" / task_id
    round_dir = create_round_dir(base, 1)
    assert not (round_dir / _bundle_filename(tmp_path)).exists()

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, "done", "validated")

    msg = str(exc.value).lower()
    assert _bundle_filename(tmp_path).lower() in msg
    assert "missing" in msg or "incomplete" in msg


def test_validator_approval_fails_on_expired_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Old bundle summary beyond maxAgeDays should block as expired."""
    task_id = "VAL-003"

    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)

    base = tmp_path / ".project" / "qa" / "validation-reports" / task_id
    round_dir = create_round_dir(base, 1)
    rpt = round_dir / _bundle_filename(tmp_path)
    _write_bundle(rpt, approved=True)

    # Set mtime to 2 days ago and require maxAgeDays=1
    old = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    os.utime(rpt, (old, old))

    task = {"id": task_id}
    engine = RulesEngine(_create_config(require=True, max_age_days=1))

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, "done", "validated")

    assert "expired" in str(exc.value).lower()


def test_validator_approval_includes_failed_validators_in_error_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When bundle approved=false, error should list failing validators."""
    task_id = "VAL-FAILED-VALIDATORS"

    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)

    base = tmp_path / ".project" / "qa" / "validation-reports" / task_id
    round_dir = create_round_dir(base, 1)
    rpt = round_dir / _bundle_filename(tmp_path)

    failing_bundle = {
        "taskId": task_id,
        "round": 1,
        "approved": False,
        "validators": [
            {"validatorId": "global-codex", "approved": True, "verdict": "approve"},
            {"validatorId": "global-claude", "approved": False, "verdict": "reject"},
            {"validatorId": "security", "approved": False, "verdict": "blocked"},
        ],
        "missing": ["performance"],
    }
    _write_bundle(rpt, payload=failing_bundle, approved=False)

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, "done", "validated")

    msg = str(exc.value).lower()
    assert "not approved" in msg
    # All failing/missing validators should be surfaced
    for vid in ("global-claude", "security", "performance"):
        assert vid in msg


def test_validator_approval_allows_when_bundle_approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Bundle summary with approved=true should allow transition via implicit lookup."""
    task_id = "VAL-IMPLICIT-APPROVED"

    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)

    base = tmp_path / ".project" / "qa" / "validation-reports" / task_id
    round_dir = create_round_dir(base, 2)
    rpt = round_dir / _bundle_filename(tmp_path)
    _write_bundle(rpt, approved=True)

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    assert engine.check_state_transition(task, "done", "validated") == []


def test_validator_approval_uses_latest_round_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Latest round-N directory should be used, not mtime heuristics."""
    task_id = "VAL-LATEST-ROUND"

    monkeypatch.chdir(tmp_path)
    setup_project_root(monkeypatch, tmp_path)

    base = tmp_path / ".project" / "qa" / "validation-reports" / task_id
    round1 = create_round_dir(base, 1)
    round3 = create_round_dir(base, 3)

    rpt1 = round1 / _bundle_filename(tmp_path)
    rpt3 = round3 / _bundle_filename(tmp_path)
    _write_bundle(rpt1, approved=False)
    _write_bundle(rpt3, approved=True)

    # Make round-1 bundle newer to catch mtime-based bugs
    now = datetime.now(timezone.utc).timestamp()
    os.utime(rpt3, (now - 10, now - 10))
    os.utime(rpt1, (now, now))

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    # Correct behavior: choose round-3 (approved=True) by round number
    assert engine.check_state_transition(task, "done", "validated") == []
