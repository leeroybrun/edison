from __future__ import annotations

from pathlib import Path

import pytest

from edison.core import task  # type: ignore
from edison.core.rules import RuleViolationError 
def _rules_cfg() -> dict:
    """Minimal config enabling validator-approval rule on validated state."""
    return {
        "rules": {
            "enforcement": True,
            "byState": {
                "validated": [
                    {
                        "id": "validator-approval",
                        "description": "Must have validator approvals",
                        "enforced": True,
                        "blocking": True,
                        "config": {
                            "requireReport": True,
                            "maxAgeDays": 7,
                        },
                    }
                ]
            },
        }
    }


def _patch_task_roots(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point task ROOT/TASK/QA/SESSION directories at isolated project root."""
    monkeypatch.setattr(task, "ROOT", root)
    monkeypatch.setattr(task, "TASK_ROOT", (root / ".project" / "tasks").resolve())
    monkeypatch.setattr(task, "QA_ROOT", (root / ".project" / "qa").resolve())
    monkeypatch.setattr(
        task,
        "SESSIONS_ROOT",
        (root / ".project" / "sessions").resolve(),
    )


@pytest.mark.task
def test_transition_task_blocks_without_validator_approval(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """transition_task should block done→validated when no bundle-approved.json exists."""
    root = isolated_project_env
    _patch_task_roots(root, monkeypatch)

    # Ensure metadata root exists
    (root / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)

    # Create JSON task record and mark it as done
    task_id = "task-001"
    task.create_task_record(task_id, "validator-approval integration test")
    task.update_task_record(
        task_id,
        {"state": "done", "status": "done"},
        operation="seed-state",
    )

    with pytest.raises(RuleViolationError):
        task.transition_task(task_id, "validated", config=_rules_cfg())


@pytest.mark.task
def test_transition_task_allows_when_bundle_approved(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """transition_task should allow done→validated when bundle-approved.json approved=true."""
    root = isolated_project_env
    _patch_task_roots(root, monkeypatch)

    # Ensure metadata and evidence roots exist
    (root / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    evidence_root = root / ".project" / "qa" / "validation-evidence"

    # Create JSON task record and mark as done
    task_id = "task-002"
    task.create_task_record(task_id, "validator-approval success path")
    task.update_task_record(
        task_id,
        {"state": "done", "status": "done"},
        operation="seed-state",
    )

    # Seed bundle-approved.json for latest evidence round
    round_dir = evidence_root / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = round_dir / "bundle-approved.json"
    bundle_path.write_text('{"taskId": "%s", "round": 1, "approved": true}' % task_id)

    # Act: transition done→validated with rules enabled
    rec = task.transition_task(task_id, "validated", config=_rules_cfg())

    # Assert: state updated and history entry added
    assert rec.get("state") == "validated"
    history = rec.get("stateHistory") or []
    assert any(h.get("to") == "validated" for h in history)

