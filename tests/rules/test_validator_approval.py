"""Tests for validator-approval rule checker."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from edison.core.rules import RulesEngine, RuleViolationError
from tests.helpers import format_round_dir, create_round_dir
from tests.helpers.io_utils import write_json


@pytest.fixture(autouse=True)
def clear_path_caches():
    """Clear path singleton cache before each test."""
    from edison.core.utils.paths import management
    management._paths_instance = None
    yield
    management._paths_instance = None


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


def _report_path(task_id: str, round_no: int = 1) -> Path:
    return (
        Path(".project/qa/validation-evidence")
        / task_id
        / format_round_dir(round_no)
        / "bundle-approved.json"
    ).resolve()


def _write_bundle(path: Path, payload: dict | None = None, *, approved: bool = True) -> None:
    """Helper to write a bundle-approved.json file."""
    data = dict(payload or {})
    # approved flag always wins if explicitly passed
    data.setdefault("approved", bool(approved))
    write_json(path, data)


def test_validator_approval_passes_with_explicit_recent_report(tmp_path: Path):
    """Explicit reportPath with approved=true should allow transition."""
    task_id = "VAL-001"
    rpt = _report_path(task_id)
    _write_bundle(rpt, approved=True)
    task = {"id": task_id, "validation": {"reportPath": str(rpt)}}

    engine = RulesEngine(_create_config())

    assert engine.check_state_transition(task, "done", "validated") == []


def test_validator_approval_blocks_when_missing_evidence_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No evidence dir → blocking RuleViolationError mentioning 'no evidence'."""
    task_id = "VAL-NO-EVIDENCE"

    # Isolated fake project root with no .project/qa tree
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, "done", "validated")

    msg = str(exc.value).lower()
    assert "no evidence" in msg


def test_validator_approval_blocks_when_no_bundle_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Evidence round exists but bundle-approved.json missing → blocks with clear message."""
    task_id = "VAL-NO-BUNDLE"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    base = tmp_path / ".project" / "qa" / "validation-evidence" / task_id
    round_dir = create_round_dir(base, 1)
    assert not (round_dir / "bundle-approved.json").exists()

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, "done", "validated")

    msg = str(exc.value).lower()
    assert "bundle-approved.json" in msg
    assert "missing" in msg or "incomplete" in msg


def test_validator_approval_fails_on_expired_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Old bundle-approved.json beyond maxAgeDays should block as expired."""
    task_id = "VAL-003"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    base = tmp_path / ".project" / "qa" / "validation-evidence" / task_id
    round_dir = create_round_dir(base, 1)
    rpt = round_dir / "bundle-approved.json"
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
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    base = tmp_path / ".project" / "qa" / "validation-evidence" / task_id
    round_dir = create_round_dir(base, 1)
    rpt = round_dir / "bundle-approved.json"

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
    """bundle-approved.json with approved=true should allow transition via implicit lookup."""
    task_id = "VAL-IMPLICIT-APPROVED"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    base = tmp_path / ".project" / "qa" / "validation-evidence" / task_id
    round_dir = create_round_dir(base, 2)
    rpt = round_dir / "bundle-approved.json"
    _write_bundle(rpt, approved=True)

    engine = RulesEngine(_create_config(require=True))
    task = {"id": task_id}

    assert engine.check_state_transition(task, "done", "validated") == []


def test_validator_approval_uses_latest_round_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Latest round-N directory should be used, not mtime heuristics."""
    task_id = "VAL-LATEST-ROUND"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    base = tmp_path / ".project" / "qa" / "validation-evidence" / task_id
    round1 = create_round_dir(base, 1)
    round3 = create_round_dir(base, 3)

    rpt1 = round1 / "bundle-approved.json"
    rpt3 = round3 / "bundle-approved.json"
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
