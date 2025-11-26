import pytest
import sys
from types import ModuleType

def test_evidence_package_structure():
    """Test that the evidence module is now a package with specific submodules."""
    # We expect these modules to exist after the split
    expected_modules = [
        "edison.core.qa.evidence.manager",
        "edison.core.qa.evidence.helpers",
        "edison.core.qa.evidence.followups",
        "edison.core.qa.evidence.analysis",
    ]
    
    for module_name in expected_modules:
        try:
            __import__(module_name)
        except ImportError:
            pytest.fail(f"Could not import {module_name}. The split has not been implemented yet.")

def test_public_api_reexports():
    """Test that all public APIs are available from the top-level package."""
    try:
        import edison.core.qa.evidence as evidence
    except ImportError:
        pytest.fail("Could not import edison.core.qa.evidence")

    # Check for symbols that should be re-exported
    expected_symbols = [
        "EvidenceError",
        "EvidenceManager",
        "get_evidence_manager",
        "missing_evidence_blockers",
        "read_validator_jsons",
        "load_impl_followups",
        "load_bundle_followups",
        "_task_evidence_root",
        "get_evidence_dir",
        "get_latest_round",
        "get_implementation_report_path",
        "list_evidence_files",
        "has_required_evidence",
    ]

    for symbol in expected_symbols:
        assert hasattr(evidence, symbol), f"Symbol {symbol} not found in edison.core.qa.evidence"

def test_module_separation():
    """Test that code is actually split into different files (implied by import success)."""
    # This test will naturally fail if the files don't exist
    try:
        from edison.core.qa.evidence.manager import EvidenceManager
        from edison.core.qa.evidence.helpers import get_evidence_dir
        from edison.core.qa.evidence.followups import load_impl_followups
        from edison.core.qa.evidence.analysis import missing_evidence_blockers
    except ImportError as e:
        pytest.fail(f"Failed to import from specific submodule: {e}")
