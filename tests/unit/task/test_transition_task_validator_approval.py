"""Tests for validator-approval rule enforcement on task validation state transition.

These tests verify that:
1. Tasks cannot transition to 'validated' state without a validation summary file
2. Tasks CAN transition to 'validated' state when validation-summary.md exists with approved=true

Uses the new repository pattern and RulesEngine API (replacing legacy task.transition_task).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from tests.helpers.env_setup import setup_project_root
from edison.core.task.repository import TaskRepository
from edison.core.task.models import Task
from edison.core.rules import RulesEngine, RuleViolationError
from edison.core.entity import EntityMetadata


def _rules_cfg() -> Dict[str, Any]:
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


@pytest.mark.task
def test_transition_task_blocks_without_validator_approval(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task transition to validated should block when no validation summary exists."""
    root = isolated_project_env
    setup_project_root(monkeypatch, root)
    monkeypatch.chdir(root)

    # Ensure task directories exist
    (root / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (root / ".project" / "tasks" / "validated").mkdir(parents=True, exist_ok=True)

    # Create task record in done state
    task_id = "task-001"
    task_repo = TaskRepository(project_root=root)
    task = Task(
        id=task_id,
        title="validator-approval integration test",
        description="Test task for validator-approval rule",
        state="done",
        metadata=EntityMetadata.create(),
    )
    task_repo.save(task)

    # Create rules engine with validator-approval rule
    engine = RulesEngine(_rules_cfg())

    # Convert task to dict for rule checking (as done in real workflows)
    task_dict = {"id": task_id}

    # Rule check should fail because no validation-summary.md exists
    with pytest.raises(RuleViolationError) as exc_info:
        engine.check_state_transition(task_dict, "done", "validated")

    # Verify the error mentions evidence/validation issue (rule enforcement worked)
    error_msg = str(exc_info.value).lower()
    assert "evidence" in error_msg or "validator" in error_msg or "approval" in error_msg


@pytest.mark.task
def test_transition_task_allows_when_bundle_approved(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task transition to validated should succeed when validation summary has approved=true."""
    root = isolated_project_env
    setup_project_root(monkeypatch, root)
    monkeypatch.chdir(root)

    # Ensure directories exist
    (root / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (root / ".project" / "tasks" / "validated").mkdir(parents=True, exist_ok=True)

    # Create task record in done state
    task_id = "task-002"
    task_repo = TaskRepository(project_root=root)
    task = Task(
        id=task_id,
        title="validator-approval success path",
        description="Test task that should pass validation",
        state="done",
        metadata=EntityMetadata.create(),
    )
    task_repo.save(task)

    # Seed evidence for round (required by can_finish_task guard)
    evidence_root = root / ".project" / "qa" / "validation-reports"
    round_dir = evidence_root / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)
    
    # Create implementation report (required by can_finish_task guard)
    impl_report = round_dir / "implementation-report.md"
    impl_report.write_text(
        f"""---
taskId: "{task_id}"
round: 1
status: "complete"
summary: "Test implementation"
---
""",
        encoding="utf-8",
    )
    
    # Create bundle summary (required by validator-approval rule).
    from edison.core.qa.evidence import EvidenceService

    bundle_path = round_dir / EvidenceService(task_id, project_root=root).bundle_filename
    bundle_path.write_text(
        f"""---
taskId: "{task_id}"
round: 1
approved: true
--- 
""",
        encoding="utf-8",
    )

    # Create rules engine with validator-approval rule
    engine = RulesEngine(_rules_cfg())

    # Convert task to dict for rule checking
    task_dict = {"id": task_id}

    # Rule check should pass (returns empty list of violations)
    violations = engine.check_state_transition(task_dict, "done", "validated")
    assert violations == []

    # Now perform the actual state transition using repository method
    loaded_task = task_repo.get(task_id)
    assert loaded_task is not None
    assert loaded_task.state == "done"

    # Transition the task to validated state via repository
    transitioned_task = task_repo.transition(task_id, "validated")

    # Assert state was updated
    assert transitioned_task.state == "validated"

    # Verify history was recorded
    assert len(transitioned_task.state_history) > 0
    last_entry = transitioned_task.state_history[-1]
    assert last_entry.from_state == "done"
    assert last_entry.to_state == "validated"
