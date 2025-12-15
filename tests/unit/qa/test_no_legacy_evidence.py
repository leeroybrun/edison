"""Test that legacy evidence manager files have been deleted."""
import pytest


def test_evidence_manager_deleted():
    """evidence.manager module should not exist."""
    with pytest.raises(ImportError):
        from edison.core.qa.evidence import manager


def test_evidence_manager_base_deleted():
    """evidence.manager_base module should not exist."""
    with pytest.raises(ImportError):
        from edison.core.qa.evidence import manager_base


def test_evidence_manager_read_deleted():
    """evidence.manager_read module should not exist."""
    with pytest.raises(ImportError):
        from edison.core.qa.evidence import manager_read


def test_evidence_manager_write_deleted():
    """evidence.manager_write module should not exist."""
    with pytest.raises(ImportError):
        from edison.core.qa.evidence import manager_write


def test_evidence_helpers_deleted():
    """evidence.helpers module should not exist."""
    with pytest.raises(ImportError):
        from edison.core.qa.evidence import helpers


def test_qa_rounds_deleted():
    """qa.rounds module should not exist."""
    with pytest.raises(ImportError):
        from edison.core.qa import rounds


def test_no_evidence_manager_in_public_api():
    """EvidenceManager should not be exported from evidence package."""
    from edison.core.qa import evidence

    assert not hasattr(evidence, "EvidenceManager"), \
        "EvidenceManager should not be exported - use EvidenceService instead"
    assert not hasattr(evidence, "get_evidence_manager"), \
        "get_evidence_manager should not be exported - use EvidenceService instead"


def test_evidence_service_available():
    """EvidenceService should be available as the new API."""
    from edison.core.qa import evidence

    assert hasattr(evidence, "EvidenceService"), \
        "EvidenceService should be exported as the new evidence API"


def test_helper_functions_not_exported():
    """Helper functions from helpers.py should not be exported."""
    from edison.core.qa import evidence

    # These were from helpers.py and should not be in public API
    legacy_helpers = [
        "_task_evidence_root",
        "get_evidence_dir",
        "get_latest_round",
        "get_implementation_report_path",
        "list_evidence_files",
    ]

    for helper in legacy_helpers:
        assert not hasattr(evidence, helper), \
            f"{helper} should not be exported - functionality is in EvidenceService"


def test_essential_functions_still_available():
    """Essential functions should still be available."""
    from edison.core.qa import evidence

    # These are essential and should remain
    assert hasattr(evidence, "EvidenceError")
    assert hasattr(evidence, "missing_evidence_blockers")
    assert hasattr(evidence, "read_validator_reports")
    assert hasattr(evidence, "load_impl_followups")
    assert hasattr(evidence, "load_bundle_followups")
    assert hasattr(evidence, "has_required_evidence")
