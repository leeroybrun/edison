#!/usr/bin/env python3
"""
Test for merged CursorAdapter functionality from adapters/cursor.py.

This test verifies that ALL functionality from root cursor_adapter.py
has been successfully merged into adapters/cursor.py.
"""

import pytest
from pathlib import Path


def test_cursor_adapter_imports_from_adapters_module():
    """Ensure CursorAdapter can be imported from edison.core.adapters.cursor."""
    from edison.core.adapters.cursor import CursorAdapter
    assert CursorAdapter is not None


def test_cursor_adapter_has_full_root_functionality():
    """Verify merged CursorAdapter has all methods from root cursor_adapter.py."""
    from edison.core.adapters.cursor import CursorAdapter

    # Core methods from root implementation
    required_methods = [
        'sync_to_cursorrules',
        'sync_structured_rules',
        'detect_cursor_overrides',
        'merge_cursor_overrides',
        'sync_agents_to_cursor',
    ]

    for method_name in required_methods:
        assert hasattr(CursorAdapter, method_name), f"Missing method: {method_name}"


def test_cursor_adapter_has_autogen_constants():
    """Verify AUTOGEN_BEGIN and AUTOGEN_END constants exist."""
    from edison.core.adapters.cursor import AUTOGEN_BEGIN, AUTOGEN_END

    assert AUTOGEN_BEGIN == "<!-- EDISON_CURSOR_AUTOGEN:BEGIN -->"
    assert AUTOGEN_END == "<!-- EDISON_CURSOR_AUTOGEN:END -->"


def test_cursor_adapter_can_be_instantiated(tmp_path):
    """Verify CursorAdapter can be instantiated with project_root."""
    from edison.core.adapters.cursor import CursorAdapter

    adapter = CursorAdapter(project_root=tmp_path)
    assert adapter.repo_root == tmp_path


def test_old_cursor_adapter_import_fails():
    """Ensure old root cursor_adapter.py import path is gone (NO LEGACY)."""
    with pytest.raises(ImportError):
        from edison.core.cursor_adapter import CursorAdapter  # noqa: F401
