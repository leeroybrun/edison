#!/usr/bin/env python3
"""
Smoke tests for PalAdapter exports and basic instantiation.
"""
from __future__ import annotations

import pytest
from pathlib import Path


class TestPalAdapterExports:
    """Test that PalAdapter functionality is available from canonical location."""

    def test_can_import_pal_adapter_from_adapters(self):
        """Verify PalAdapter is importable from canonical location."""
        from edison.core.adapters import PalAdapter

        assert PalAdapter is not None
        assert hasattr(PalAdapter, '__init__')

    def test_pal_adapter_exposes_key_methods(self):
        """Verify PalAdapter exposes key methods expected by composition."""
        from edison.core.adapters import PalAdapter

        assert PalAdapter is not None
        assert hasattr(PalAdapter, '__init__')
        # Verify key methods from implementation exist
        assert hasattr(PalAdapter, 'get_applicable_guidelines')
        assert hasattr(PalAdapter, 'get_applicable_rules')
        assert hasattr(PalAdapter, 'compose_pal_prompt')
        assert hasattr(PalAdapter, 'sync_role_prompts')
        assert hasattr(PalAdapter, 'verify_cli_prompts')

    def test_can_import_workflow_heading_constant(self):
        """Verify WORKFLOW_HEADING constant is available."""
        from edison.core.adapters import WORKFLOW_HEADING

        assert WORKFLOW_HEADING is not None
        assert isinstance(WORKFLOW_HEADING, str)
        assert "Edison Workflow Loop" in WORKFLOW_HEADING

    def test_pal_adapter_instantiation(self, tmp_path: Path):
        """Verify PalAdapter can be instantiated."""
        from edison.core.adapters import PalAdapter

        # Create minimal directory structure
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # PalAdapter should instantiate without errors
        adapter = PalAdapter(project_root=repo_root, config={})

        assert adapter is not None
        assert adapter.project_root == repo_root

    # NOTE: We intentionally do not test legacy import paths here.
