"""Tests for EvidenceService initialization - NO MOCKS."""
from __future__ import annotations

from edison.core.qa.evidence.service import EvidenceService


def test_evidence_service_initialization(isolated_project_env):
    """EvidenceService initializes with correct paths."""
    svc = EvidenceService(task_id="T-123", project_root=isolated_project_env)

    # Should resolve to .project/qa/validation-evidence/T-123
    expected = isolated_project_env / ".project" / "qa" / "validation-evidence" / "T-123"
    assert svc.get_evidence_root() == expected
    assert svc.task_id == "T-123"
    assert svc.project_root == isolated_project_env
