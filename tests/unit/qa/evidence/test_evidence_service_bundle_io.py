"""Tests for EvidenceService bundle report I/O - NO MOCKS."""
from __future__ import annotations

from edison.core.qa.evidence.service import EvidenceService


def test_evidence_service_save_and_load_bundle_report(isolated_project_env):
    """EvidenceService can save and load bundle reports."""
    svc = EvidenceService(task_id="T-100", project_root=isolated_project_env)

    # Create round
    svc.ensure_round()

    # Save bundle report
    bundle_data = {
        "status": "approved",
        "files": ["file1.py", "file2.py"],
        "score": 95
    }
    svc.write_bundle(bundle_data)

    # Load bundle report
    loaded = svc.read_bundle()
    assert loaded == bundle_data
