#!/usr/bin/env python3
"""
Test merged ZenAdapter functionality from adapters/zen.py

This test verifies that BOTH old and new ZenAdapter implementations
are available from the adapters module after the merge.

RED: This test will fail initially because the merge hasn't happened yet.
GREEN: After merging, both ZenAdapter and ZenPromptAdapter will be importable.
"""
from __future__ import annotations

import pytest
from pathlib import Path


class TestZenAdapterMerged:
    """Test that both ZenAdapter architectures coexist after merge."""

    def test_can_import_zen_prompt_adapter_from_adapters_zen(self):
        """Verify ZenPromptAdapter (new architecture) is importable."""
        from edison.core.adapters.zen import ZenPromptAdapter

        assert ZenPromptAdapter is not None
        assert hasattr(ZenPromptAdapter, '__init__')

    def test_can_import_zen_adapter_from_adapters_zen(self):
        """Verify ZenAdapter (old architecture) is importable from adapters.zen."""
        from edison.core.adapters.zen import ZenAdapter

        assert ZenAdapter is not None
        assert hasattr(ZenAdapter, '__init__')
        # Verify key methods from old implementation exist
        assert hasattr(ZenAdapter, 'get_applicable_guidelines')
        assert hasattr(ZenAdapter, 'get_applicable_rules')
        assert hasattr(ZenAdapter, 'compose_zen_prompt')
        assert hasattr(ZenAdapter, 'sync_role_prompts')
        assert hasattr(ZenAdapter, 'verify_cli_prompts')

    def test_can_import_zen_adapter_from_adapters_init(self):
        """Verify ZenAdapter is exported from adapters package."""
        from edison.core.adapters import ZenAdapter

        assert ZenAdapter is not None

    def test_can_import_workflow_heading_constant(self):
        """Verify WORKFLOW_HEADING constant is available."""
        from edison.core.adapters.zen import WORKFLOW_HEADING

        assert WORKFLOW_HEADING is not None
        assert isinstance(WORKFLOW_HEADING, str)
        assert "Edison Workflow Loop" in WORKFLOW_HEADING

    def test_zen_adapter_instantiation(self, tmp_path: Path):
        """Verify ZenAdapter can be instantiated."""
        from edison.core.adapters.zen import ZenAdapter

        # Create minimal directory structure
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # ZenAdapter should instantiate without errors
        adapter = ZenAdapter(repo_root=repo_root, config={})

        assert adapter is not None
        assert adapter.repo_root == repo_root

    def test_root_zen_adapter_import_fails(self):
        """Verify root location no longer works (NO LEGACY)."""
        with pytest.raises(ImportError):
            from edison.core.zen_adapter import ZenAdapter  # noqa: F401
