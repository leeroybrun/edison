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


def test_claude_code_adapter_import_from_adapters():
    """Test that ClaudeCodeAdapter can be imported from adapters package."""
    # RED: This should fail initially since ClaudeCodeAdapter is not in adapters/claude.py
    from edison.core.adapters.claude import ClaudeCodeAdapter

    assert ClaudeCodeAdapter is not None
    assert hasattr(ClaudeCodeAdapter, 'validate_claude_structure')
    assert hasattr(ClaudeCodeAdapter, 'sync_agents_to_claude')
    assert hasattr(ClaudeCodeAdapter, 'sync_orchestrator_to_claude')
    assert hasattr(ClaudeCodeAdapter, 'generate_claude_config')


def test_claude_code_adapter_can_be_instantiated():
    """Test that ClaudeCodeAdapter can be instantiated from adapters package."""
    from edison.core.adapters.claude import ClaudeCodeAdapter

    # Should be able to create an instance
    adapter = ClaudeCodeAdapter()
    assert adapter is not None
    assert hasattr(adapter, 'repo_root')
    assert hasattr(adapter, 'claude_dir')
    assert hasattr(adapter, 'claude_agents_dir')


def test_claude_adapter_error_is_available():
    """Test that ClaudeAdapterError exception is available."""
    from edison.core.adapters.claude import ClaudeAdapterError

    assert issubclass(ClaudeAdapterError, RuntimeError)


def test_edison_agent_sections_is_available():
    """Test that EdisonAgentSections dataclass is available."""
    from edison.core.adapters.claude import EdisonAgentSections

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
    from edison.core.adapters import claude

    expected_exports = ['ClaudeAdapter', 'ClaudeCodeAdapter', 'ClaudeAdapterError', 'EdisonAgentSections']

    for export in expected_exports:
        assert export in claude.__all__, f"Missing export: {export}"
        assert hasattr(claude, export), f"Export {export} not available as attribute"
