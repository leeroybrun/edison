"""Tests for EvidenceService edge cases and error conditions - NO MOCKS."""
from __future__ import annotations

from edison.core.qa.evidence.service import EvidenceService


def test_evidence_service_missing_report_returns_empty_dict(isolated_project_env):
    """EvidenceService returns empty dict for missing reports."""
    svc = EvidenceService(task_id="T-999", project_root=isolated_project_env)

    # Create round
    svc.ensure_round()

    # Read non-existent reports
    assert svc.read_bundle() == {}
    assert svc.read_implementation_report() == {}
    assert svc.read_validator_report("nonexistent") == {}


def test_evidence_service_multiple_tasks_isolated(isolated_project_env):
    """Different task IDs have isolated evidence directories."""
    svc1 = EvidenceService(task_id="T-001", project_root=isolated_project_env)
    svc2 = EvidenceService(task_id="T-002", project_root=isolated_project_env)

    # Create rounds and write data
    svc1.ensure_round()
    svc1.write_bundle({"task": "T-001"})

    svc2.ensure_round()
    svc2.write_bundle({"task": "T-002"})

    # Verify isolation
    data1 = svc1.read_bundle()
    data2 = svc2.read_bundle()

    assert data1 == {"task": "T-001"}
    assert data2 == {"task": "T-002"}

    # Verify paths are different
    assert svc1.get_evidence_root() != svc2.get_evidence_root()
