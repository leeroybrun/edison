#!/usr/bin/env python3
"""
Test that ClaudeCodeAdapter is available from edison.core.adapters.claude after merge.

This test ensures Wave 2-A merge is complete:
- ClaudeCodeAdapter must be importable from edison.core.adapters.claude
- All methods from the root claude_adapter.py must be available
- The class must work exactly as it did before the merge
"""
from __future__ import annotations

import pytest
from pathlib import Path


def test_claude_sync_import_from_adapters():
    """Test that ClaudeSync can be imported from canonical adapters package."""
    from edison.core.adapters import ClaudeSync

    assert ClaudeSync is not None
    assert hasattr(ClaudeSync, 'validate_claude_structure')
    assert hasattr(ClaudeSync, 'sync_agents_to_claude')
    assert hasattr(ClaudeSync, 'sync_orchestrator_to_claude')
    assert hasattr(ClaudeSync, 'generate_claude_config')


def test_claude_sync_can_be_instantiated():
    """Test that ClaudeSync can be instantiated from canonical adapters package."""
    from edison.core.adapters import ClaudeSync

    # Should be able to create an instance
    adapter = ClaudeSync()
    assert adapter is not None
    assert hasattr(adapter, 'repo_root')
    assert hasattr(adapter, 'claude_dir')
    assert hasattr(adapter, 'claude_agents_dir')


def test_claude_adapter_error_is_available():
    """Test that ClaudeAdapterError exception is available."""
    from edison.core.adapters import ClaudeAdapterError

    assert issubclass(ClaudeAdapterError, RuntimeError)


def test_edison_agent_sections_is_available():
    """Test that EdisonAgentSections dataclass is available."""
    from edison.core.adapters import EdisonAgentSections

    # Should be a dataclass
    sections = EdisonAgentSections(
        name="test",
        role="test role",
        tools="test tools",
        guidelines="test guidelines",
        workflows="test workflows"
    )
    assert sections.name == "test"
    assert sections.role == "test role"


def test_root_claude_adapter_import_fails():
    """Test that importing from root claude_adapter.py fails (NO LEGACY)."""
    with pytest.raises(ImportError):
        from edison.core.claude_adapter import ClaudeCodeAdapter  # noqa: F401


def test_all_exports_are_complete():
    """Test that __all__ includes all necessary exports."""
    from edison.core import adapters

    expected_exports = ['ClaudeAdapter', 'ClaudeSync', 'ClaudeAdapterError', 'EdisonAgentSections']

    for export in expected_exports:
        assert export in adapters.__all__, f"Missing export: {export}"
        assert hasattr(adapters, export), f"Export {export} not available as attribute"
