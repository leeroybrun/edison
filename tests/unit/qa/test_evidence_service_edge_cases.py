"""Tests for EvidenceService edge cases and error conditions - NO MOCKS."""
from __future__ import annotations

import pytest
from pathlib import Path

from edison.core.qa.evidence.service import EvidenceService


@pytest.fixture(autouse=True)
def clear_path_caches():
    """Clear path singleton cache before each test."""
    from edison.core.utils.paths import management
    management._paths_instance = None
    yield
    management._paths_instance = None


@pytest.fixture
def project_root(tmp_path):
    """Create a real project structure with .edison config."""
    root = tmp_path / "project"
    root.mkdir()

    # Create .edison config
    edison_dir = root / ".edison"
    edison_dir.mkdir()
    config_file = edison_dir / "config.yml"
    config_file.write_text("management_dir: .project\n")

    return root


def test_evidence_service_missing_report_returns_empty_dict(project_root):
    """EvidenceService returns empty dict for missing reports."""
    svc = EvidenceService(task_id="T-999", project_root=project_root)

    # Create round
    svc.ensure_round()

    # Read non-existent reports
    assert svc.read_bundle() == {}
    assert svc.read_implementation_report() == {}
    assert svc.read_validator_report("nonexistent") == {}


def test_evidence_service_multiple_tasks_isolated(project_root):
    """Different task IDs have isolated evidence directories."""
    svc1 = EvidenceService(task_id="T-001", project_root=project_root)
    svc2 = EvidenceService(task_id="T-002", project_root=project_root)

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
