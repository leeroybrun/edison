#!/usr/bin/env python3
"""
Test merged ZenAdapter functionality from adapters/zen.py

This test verifies that BOTH old and new ZenAdapter implementations
are available from the adapters module after the merge.

RED: This test will fail initially because the merge hasn't happened yet.
GREEN: After merging, both ZenAdapter and ZenAdapter will be importable.
"""
from __future__ import annotations

import pytest
from pathlib import Path


class TestZenAdapterMerged:
    """Test that ZenAdapter functionality is available from canonical location."""

    def test_can_import_zen_prompt_adapter_from_adapters(self):
        """Verify ZenAdapter is importable from canonical location."""
        from edison.core.adapters import ZenAdapter

        assert ZenAdapter is not None
        assert hasattr(ZenAdapter, '__init__')

    def test_can_import_zen_sync_from_adapters(self):
        """Verify ZenSync (full adapter) is importable from canonical location."""
        from edison.core.adapters import ZenSync

        assert ZenSync is not None
        assert hasattr(ZenSync, '__init__')
        # Verify key methods from implementation exist
        assert hasattr(ZenSync, 'get_applicable_guidelines')
        assert hasattr(ZenSync, 'get_applicable_rules')
        assert hasattr(ZenSync, 'compose_zen_prompt')
        assert hasattr(ZenSync, 'sync_role_prompts')
        assert hasattr(ZenSync, 'verify_cli_prompts')

    def test_can_import_workflow_heading_constant(self):
        """Verify WORKFLOW_HEADING constant is available."""
        from edison.core.adapters import WORKFLOW_HEADING

        assert WORKFLOW_HEADING is not None
        assert isinstance(WORKFLOW_HEADING, str)
        assert "Edison Workflow Loop" in WORKFLOW_HEADING

    def test_zen_sync_instantiation(self, tmp_path: Path):
        """Verify ZenSync can be instantiated."""
        from edison.core.adapters import ZenSync

        # Create minimal directory structure
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # ZenSync should instantiate without errors
        adapter = ZenAdapter(project_root=repo_root, config={})

        assert adapter is not None
        assert adapter.repo_root == repo_root

    def test_root_zen_adapter_import_fails(self):
        """Verify root location no longer works (NO LEGACY)."""
        with pytest.raises(ImportError):
            from edison.core.zen_adapter import ZenAdapter  # noqa: F401
