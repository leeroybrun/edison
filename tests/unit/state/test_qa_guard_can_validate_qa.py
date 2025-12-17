from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_can_validate_qa_raises_actionable_error_when_missing_reports(isolated_project_env: Path) -> None:
    """Promotion should fail with a helpful message when approvals are missing."""
    repo = isolated_project_env

    # Minimal validator set: two blocking validators, always run.
    _write_yaml(
        repo / ".edison" / "config" / "validators.yaml",
        {
            "validation": {
                "validators": {
                    "v1": {
                        "name": "V1",
                        "engine": "zen-mcp",
                        "fallback_engine": "zen-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                        "triggers": ["*"],
                    },
                    "v2": {
                        "name": "V2",
                        "engine": "zen-mcp",
                        "fallback_engine": "zen-mcp",
                        "wave": "critical",
                        "always_run": True,
                        "blocking": True,
                        "triggers": ["*"],
                    },
                },
                "waves": [{"name": "critical"}],
            }
        },
    )
    from tests.helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    # Create a done task so QA validation would be relevant.
    task_id = "T001"
    task_dir = repo / ".project" / "tasks" / "done"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task_id}.md").write_text(
        "---\n"
        f"id: {task_id}\n"
        f"title: {task_id}\n"
        "owner: test\n"
        "created_at: '2025-12-15T00:00:00Z'\n"
        "updated_at: '2025-12-15T00:00:00Z'\n"
        "---\n\n"
        "# T001\n",
        encoding="utf-8",
    )

    # Write only ONE validator report (v1 approve), leaving v2 missing.
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=repo)
    ev.ensure_round(1)
    ev.write_validator_report(
        "v1",
        {
            "taskId": task_id,
            "round": 1,
            "validatorId": "v1",
            "model": "test",
            "zenRole": "validator-v1",
            "verdict": "approve",
            "findings": [],
            "strengths": [],
            "context7Used": False,
            "context7Packages": [],
            "evidenceReviewed": [],
            "summary": "ok",
            "followUpTasks": [],
            "tracking": {
                "processId": 1,
                "hostname": "test",
                "startedAt": "2025-12-15T00:00:00Z",
                "completedAt": "2025-12-15T00:00:00Z",
            },
        },
        round_num=1,
    )

    from edison.core.state.builtin.guards.qa import can_validate_qa

    with pytest.raises(ValueError) as exc:
        can_validate_qa({"task_id": task_id})
    assert "v2" in str(exc.value)

