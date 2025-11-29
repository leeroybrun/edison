"""Tests for EvidenceService implementation report I/O - NO MOCKS."""
from __future__ import annotations

from edison.core.qa.evidence.service import EvidenceService


def test_evidence_service_save_and_load_implementation_report(isolated_project_env):
    """EvidenceService can save and load implementation reports."""
    svc = EvidenceService(task_id="T-200", project_root=isolated_project_env)

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
