"""Tests for EvidenceService implementation report I/O - NO MOCKS."""
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


def test_evidence_service_save_and_load_implementation_report(project_root):
    """EvidenceService can save and load implementation reports."""
    svc = EvidenceService(task_id="T-200", project_root=project_root)

    # Create round
    svc.ensure_round()

    # Save implementation report
    impl_data = {
        "implementation": "complete",
        "files_modified": ["src/main.py"],
        "tests_added": ["tests/test_main.py"]
    }
    svc.write_implementation_report(impl_data)

    # Load implementation report
    loaded = svc.read_implementation_report()
    assert loaded == impl_data
