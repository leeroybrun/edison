from __future__ import annotations
from pathlib import Path
import sys

import pytest


# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

from edison.core.qa.evidence import EvidenceService
from tests.helpers import create_report_markdown


class TestEvidenceService:
    def test_get_current_round(self, isolated_project_env: Path) -> None:
        """Service resolves latest evidence round or returns None."""
        task_id = "task-100"
        svc = EvidenceService(task_id, project_root=isolated_project_env)

        # No evidence yet -> None
        assert svc.get_current_round() is None

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

        latest_num = svc.get_current_round()
        assert latest_num == 2
        
        latest_dir = svc.ensure_round(latest_num)
        assert latest_dir.name == "round-2"
        assert latest_dir.parent == evidence_base

    def test_read_bundle_summary(self, isolated_project_env: Path) -> None:
        """Service reads bundle-approved.md from latest round."""
        task_id = "task-200"
        svc = EvidenceService(task_id, project_root=isolated_project_env)

        # Missing bundle file -> returns empty dict
        assert svc.read_bundle() == {}

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
        bundle_path = round_dir / "bundle-approved.md"
        create_report_markdown(bundle_path, payload, body="\n# Bundle Approval\n")

        data = svc.read_bundle()
        assert data["approved"] is True
        assert data["taskId"] == task_id

    def test_read_implementation_report(self, isolated_project_env: Path) -> None:
        """Service reads implementation-report.md from latest round."""
        task_id = "task-300"
        svc = EvidenceService(task_id, project_root=isolated_project_env)

        # Missing report -> returns empty dict
        assert svc.read_implementation_report() == {}

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
        report_path = round_dir / "implementation-report.md"
        create_report_markdown(report_path, payload, body="\n# Implementation Report\n")

        data = svc.read_implementation_report()
        assert data["implementer"] == "test-agent"
        assert data["taskId"] == task_id
