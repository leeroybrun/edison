#!/usr/bin/env python3
"""
Test for merged CursorAdapter functionality from adapters/cursor.py.

This test verifies that ALL functionality from root cursor_adapter.py
has been successfully merged into adapters/cursor.py.
"""

import pytest
from pathlib import Path


def test_cursor_sync_imports_from_adapters_module():
    """Ensure CursorAdapter can be imported from canonical edison.core.adapters."""
    from edison.core.adapters import CursorAdapter
    assert CursorAdapter is not None


def test_cursor_sync_has_full_functionality():
    """Verify CursorAdapter has all required methods."""
    from edison.core.adapters import CursorAdapter

    # Core methods from unified adapter implementation
    required_methods = [
        'sync_to_cursorrules',
        'sync_structured_rules',
        'merge_cursor_overrides',
        'sync_agents_to_cursor',
        'sync_all',  # Unified adapter entry point
        'validate_structure',  # Directory structure validation
    ]

    for method_name in required_methods:
        assert hasattr(CursorAdapter, method_name), f"Missing method: {method_name}"


def test_cursor_adapter_has_autogen_constants():
    """Verify AUTOGEN_BEGIN and AUTOGEN_END constants exist."""
    from edison.core.adapters import AUTOGEN_BEGIN, AUTOGEN_END

    assert AUTOGEN_BEGIN == "<!-- EDISON_CURSOR_AUTOGEN:BEGIN -->"
    assert AUTOGEN_END == "<!-- EDISON_CURSOR_AUTOGEN:END -->"


def test_cursor_sync_can_be_instantiated(tmp_path):
    """Verify CursorAdapter can be instantiated with project_root."""
    from edison.core.adapters import CursorAdapter

    adapter = CursorAdapter(project_root=tmp_path)
    assert adapter.project_root == tmp_path


def test_old_cursor_adapter_import_fails():
    """Ensure old root cursor_adapter.py import path is gone (NO LEGACY)."""
    with pytest.raises(ImportError):
        from edison.core.cursor_adapter import CursorAdapter  # noqa: F401
