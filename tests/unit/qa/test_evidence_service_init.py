"""Tests for EvidenceService initialization - NO MOCKS."""
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


def test_evidence_service_initialization(project_root):
    """EvidenceService initializes with correct paths."""
    svc = EvidenceService(task_id="T-123", project_root=project_root)

    # Should resolve to .project/qa/validation-evidence/T-123
    expected = project_root / ".project" / "qa" / "validation-evidence" / "T-123"
    assert svc.get_evidence_root() == expected
    assert svc.task_id == "T-123"
    assert svc.project_root == project_root
