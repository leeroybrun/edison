"""Tests for EvidenceService validator report I/O - NO MOCKS."""
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


def test_evidence_service_save_and_load_validator_report(project_root):
    """EvidenceService can save and load validator reports."""
    svc = EvidenceService(task_id="T-300", project_root=project_root)

    # Create round
    svc.ensure_round()

    # Save validator report
    validator_data = {
        "validator": "security",
        "score": 100,
        "issues": []
    }
    svc.write_validator_report("security", validator_data)

    # Load validator report
    loaded = svc.read_validator_report("security")
    assert loaded == validator_data


def test_evidence_service_list_validator_reports(project_root):
    """EvidenceService can list validator reports."""
    svc = EvidenceService(task_id="T-400", project_root=project_root)

    # Create round
    svc.ensure_round()

    # Create multiple validator reports
    svc.write_validator_report("security", {"score": 100})
    svc.write_validator_report("performance", {"score": 95})
    svc.write_validator_report("style", {"score": 90})

    # List reports
    reports = svc.list_validator_reports()
    assert len(reports) == 3

    # Check filenames
    report_names = [r.name for r in reports]
    assert "validator-security-report.json" in report_names
    assert "validator-performance-report.json" in report_names
    assert "validator-style-report.json" in report_names
