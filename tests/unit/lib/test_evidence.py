from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from edison.core.qa.evidence import EvidenceManager  # type: ignore  # noqa: E402


class TestEvidenceManagerStatics:
    def test_get_latest_round_dir(self, isolated_project_env: Path) -> None:
        """Static helper resolves latest evidence round and fails when missing."""
        task_id = "task-100"

        # No evidence yet -> FileNotFoundError
        with pytest.raises(FileNotFoundError):
            EvidenceManager.get_latest_round_dir(task_id)  # type: ignore[attr-defined]

        # Create multiple rounds under isolated project
        evidence_base = (
            isolated_project_env
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
        )
        (evidence_base / "round-1").mkdir(parents=True, exist_ok=True)
        (evidence_base / "round-2").mkdir(parents=True, exist_ok=True)

        latest = EvidenceManager.get_latest_round_dir(task_id)  # type: ignore[attr-defined]
        assert latest.name == "round-2"
        assert latest.parent == evidence_base

    def test_read_bundle_summary(self, isolated_project_env: Path) -> None:
        """Static helper reads bundle-approved.json from latest round."""
        task_id = "task-200"

        # Missing evidence directory -> FileNotFoundError
        with pytest.raises(FileNotFoundError):
            EvidenceManager.read_bundle_summary(task_id)  # type: ignore[attr-defined]

        evidence_base = (
            isolated_project_env
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
        )
        round_dir = evidence_base / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        payload = {"approved": True, "taskId": task_id}
        bundle_path = round_dir / "bundle-approved.json"
        bundle_path.write_text(json.dumps(payload), encoding="utf-8")

        data = EvidenceManager.read_bundle_summary(task_id)  # type: ignore[attr-defined]
        assert data["approved"] is True
        assert data["taskId"] == task_id

    def test_read_implementation_report(self, isolated_project_env: Path) -> None:
        """Static helper reads implementation-report.json from latest round."""
        task_id = "task-300"

        with pytest.raises(FileNotFoundError):
            EvidenceManager.read_implementation_report(task_id)  # type: ignore[attr-defined]

        evidence_base = (
            isolated_project_env
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
        )
        round_dir = evidence_base / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        payload = {"implementer": "test-agent", "taskId": task_id}
        report_path = round_dir / "implementation-report.json"
        report_path.write_text(json.dumps(payload), encoding="utf-8")

        data = EvidenceManager.read_implementation_report(task_id)  # type: ignore[attr-defined]
        assert data["implementer"] == "test-agent"
        assert data["taskId"] == task_id

