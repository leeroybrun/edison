import pytest


def test_evidence_package_structure():
    """Test that the evidence module is now a package with specific submodules."""
    # We expect these modules to exist after the split
    expected_modules = [
        "edison.core.qa.evidence.followups",
        "edison.core.qa.evidence.analysis",
        "edison.core.qa.evidence.service",
        "edison.core.qa.evidence.rounds",
        "edison.core.qa.evidence.reports",
    ]

    for module_name in expected_modules:
        try:
            __import__(module_name)
        except ImportError:
            pytest.fail(f"Could not import {module_name}. Expected module is missing.")


def test_public_api_reexports():
    """Test that all public APIs are available from the top-level package."""
    import edison.core.qa.evidence as evidence

    # Check for symbols that should be re-exported
    expected_symbols = [
        "EvidenceError",
        "EvidenceService",
        "missing_evidence_blockers",
        "read_validator_jsons",
        "load_impl_followups",
        "load_bundle_followups",
        "has_required_evidence",
    ]

    for symbol in expected_symbols:
        assert hasattr(evidence, symbol), f"Symbol {symbol} not found in edison.core.qa.evidence"


def test_legacy_modules_deleted():
    """Test that legacy manager and helpers modules have been deleted."""
    legacy_modules = [
        "edison.core.qa.evidence.manager",
        "edison.core.qa.evidence.manager_base",
        "edison.core.qa.evidence.manager_read",
        "edison.core.qa.evidence.manager_write",
        "edison.core.qa.evidence.helpers",
    ]

    for module_name in legacy_modules:
        with pytest.raises(ImportError):
            __import__(module_name)


def test_module_separation():
    """Test that code is actually split into different files."""
    from edison.core.qa.evidence.followups import load_impl_followups
    from edison.core.qa.evidence.analysis import missing_evidence_blockers
    from edison.core.qa.evidence.service import EvidenceService
    from edison.core.qa.evidence import rounds
    from edison.core.qa.evidence import reports
