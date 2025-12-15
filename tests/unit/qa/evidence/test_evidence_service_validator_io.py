"""Tests for EvidenceService validator report I/O - NO MOCKS."""
from __future__ import annotations

from edison.core.qa.evidence.service import EvidenceService


def test_evidence_service_save_and_load_validator_report(isolated_project_env):
    """EvidenceService can save and load validator reports."""
    svc = EvidenceService(task_id="T-300", project_root=isolated_project_env)

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


def test_evidence_service_list_validator_reports(isolated_project_env):
    """EvidenceService can list validator reports."""
    svc = EvidenceService(task_id="T-400", project_root=isolated_project_env)

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
    assert "validator-security-report.md" in report_names
    assert "validator-performance-report.md" in report_names
    assert "validator-style-report.md" in report_names
