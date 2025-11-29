#!/usr/bin/env python3
from __future__ import annotations

"""
Test audit package structure after refactoring from single file to package.

Verifies:
- All public APIs are accessible from audit package
- Discovery, analysis, and purity modules exist and export correctly
- Backward compatibility with existing imports
- NO MOCKS - tests real imports and module structure
"""

import pytest
from pathlib import Path


def test_audit_package_exists():
    """Audit must be a package (directory with __init__.py), not a single file."""
    from edison.core.composition import audit

    audit_path = Path(audit.__file__).parent
    assert audit_path.is_dir(), "audit must be a package directory"
    assert (audit_path / "__init__.py").exists(), "audit package must have __init__.py"


def test_discovery_module_exists():
    """Discovery module must exist with guideline discovery functions."""
    from edison.core.composition.audit import guideline_discovery

    # Verify module has expected functions
    assert hasattr(guideline_discovery, "discover_guidelines")
    assert hasattr(guideline_discovery, "GuidelineRecord")
    assert hasattr(guideline_discovery, "GuidelineCategory")
    assert callable(guideline_discovery.discover_guidelines)


def test_analysis_module_exists():
    """Analysis module must exist with duplication detection functions."""
    from edison.core.composition.audit import analysis

    # Verify module has expected functions
    assert hasattr(analysis, "build_shingle_index")
    assert hasattr(analysis, "duplication_matrix")
    assert callable(analysis.build_shingle_index)
    assert callable(analysis.duplication_matrix)


def test_purity_module_exists():
    """Purity module must exist with cross-layer checking functions."""
    from edison.core.composition.audit import purity

    # Verify module has expected functions
    assert hasattr(purity, "purity_violations")
    assert hasattr(purity, "project_terms")
    assert hasattr(purity, "DEFAULT_PROJECT_TERMS")
    assert hasattr(purity, "PACK_TECH_TERMS")
    assert callable(purity.purity_violations)
    assert callable(purity.project_terms)


def test_backward_compatibility_main_exports():
    """All previous audit.py exports must still be accessible from audit package."""
    from edison.core.composition import audit

    # Discovery exports
    assert hasattr(audit, "GuidelineRecord")
    assert hasattr(audit, "GuidelineCategory")
    assert hasattr(audit, "discover_guidelines")

    # Analysis exports
    assert hasattr(audit, "build_shingle_index")
    assert hasattr(audit, "duplication_matrix")

    # Purity exports
    assert hasattr(audit, "purity_violations")
    assert hasattr(audit, "project_terms")
    assert hasattr(audit, "DEFAULT_PROJECT_TERMS")
    assert hasattr(audit, "PACK_TECH_TERMS")


def test_composition_package_exports_audit_functions():
    """Composition package must re-export all audit functions for backward compatibility."""
    from edison.core import composition

    # Verify all audit exports are available at composition level
    assert hasattr(composition, "GuidelineRecord")
    assert hasattr(composition, "GuidelineCategory")
    assert hasattr(composition, "discover_guidelines")
    assert hasattr(composition, "build_shingle_index")
    assert hasattr(composition, "duplication_matrix")
    assert hasattr(composition, "purity_violations")
    assert hasattr(composition, "project_terms")
    assert hasattr(composition, "DEFAULT_PROJECT_TERMS")
    assert hasattr(composition, "PACK_TECH_TERMS")


def test_no_circular_imports():
    """Verify no circular import issues between audit modules."""
    # If this test runs without ImportError, circular imports are not present
    from edison.core.composition.audit import guideline_discovery
    from edison.core.composition.audit import analysis
    from edison.core.composition.audit import purity

    # All modules should be importable without errors
    assert guideline_discovery is not None
    assert analysis is not None
    assert purity is not None


def test_discovery_functions_work():
    """Discovery functions must be callable and return correct types."""
    from edison.core.composition.audit import discover_guidelines, GuidelineRecord

    # discover_guidelines should return a list
    result = discover_guidelines()
    assert isinstance(result, list)

    # If results exist, they should be GuidelineRecord instances
    if result:
        assert all(isinstance(r, GuidelineRecord) for r in result)


def test_analysis_functions_work():
    """Analysis functions must be callable and return correct types."""
    from edison.core.composition.audit import build_shingle_index, duplication_matrix, GuidelineRecord
    from pathlib import Path

    # Create empty record list for testing
    records = []

    # build_shingle_index should return a dict
    index = build_shingle_index(records)
    assert isinstance(index, dict)

    # duplication_matrix should return a list
    matrix = duplication_matrix(records)
    assert isinstance(matrix, list)


def test_purity_functions_work():
    """Purity checking functions must be callable and return correct types."""
    from edison.core.composition.audit import purity_violations, project_terms

    # project_terms should return a list of strings
    terms = project_terms()
    assert isinstance(terms, list)
    assert all(isinstance(t, str) for t in terms)

    # purity_violations should return a dict with specific keys
    violations = purity_violations([])
    assert isinstance(violations, dict)
    assert "core_project_terms" in violations
    assert "pack_project_terms" in violations
    assert "project_pack_terms" in violations


def test_old_audit_py_file_does_not_exist():
    """Old audit.py file must be deleted after split."""
    from edison.core.composition import audit

    audit_path = Path(audit.__file__).parent
    old_file = audit_path.parent / "audit.py"

    assert not old_file.exists(), "Old audit.py file must be deleted after splitting into package"
