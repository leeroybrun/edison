"""Tests for convenience functions in output config.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader, get_output_config


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_output_config_convenience_function(self, tmp_path: Path) -> None:
        """get_output_config should return a loader instance."""
        loader = get_output_config(repo_root=tmp_path)

        assert isinstance(loader, OutputConfigLoader)
        assert loader.project_root == tmp_path
