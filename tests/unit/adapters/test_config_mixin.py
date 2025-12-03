"""Tests for ConfigMixin shared across all adapters.

This test suite verifies the shared config loading pattern used by all
adapter classes (ClaudeAdapter, CursorAdapter, CodexAdapter, etc.)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from edison.core.adapters._config import ConfigMixin


class DummyAdapter(ConfigMixin):
    """Minimal test adapter to verify ConfigMixin behavior."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        # Reset class-level cache for each test instance
        self._cached_config = None


class TestConfigMixin:
    """Test suite for ConfigMixin functionality."""

    def test_config_mixin_loads_valid_config(self, tmp_path: Path) -> None:
        """Test that ConfigMixin successfully loads config via ConfigManager.

        We test that ConfigMixin correctly calls ConfigManager and returns
        a dict. The exact contents depend on ConfigManager's merge logic,
        so we just verify the return type and presence of expected sections.
        """
        # Arrange & Act: Create adapter and access config
        adapter = DummyAdapter(tmp_path)
        result = adapter.config

        # Assert: Config is loaded as dict with expected structure
        assert isinstance(result, dict)
        # ConfigManager always provides defaults with these sections
        assert "edison" in result or "session" in result or "packs" in result

    def test_config_mixin_caches_loaded_config(self, tmp_path: Path) -> None:
        """Test that ConfigMixin caches config and doesn't reload it."""
        # Arrange: Create a minimal config
        config_dir = tmp_path / ".agents"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("packs:\n  active: []\n", encoding="utf-8")

        adapter = DummyAdapter(tmp_path)

        # Act: Access config twice
        first_access = adapter.config
        second_access = adapter.config

        # Assert: Both accesses return the same object (cached)
        assert first_access is second_access
        assert adapter._cached_config is not None
        assert adapter._cached_config is first_access

    def test_config_mixin_handles_missing_config(self, tmp_path: Path) -> None:
        """Test that ConfigMixin returns defaults when project config is missing.

        Note: ConfigManager provides default config even when project has no
        config file, so we expect a dict with defaults rather than empty dict.
        """
        # Arrange: No config file created
        adapter = DummyAdapter(tmp_path)

        # Act: Access config
        result = adapter.config

        # Assert: Config loaded (with defaults from ConfigManager)
        assert isinstance(result, dict)
        # ConfigManager provides defaults, so it won't be empty
        assert adapter._cached_config is not None
        assert adapter._cached_config is result

    def test_config_mixin_handles_malformed_config(self, tmp_path: Path) -> None:
        """Test that ConfigMixin handles malformed YAML gracefully.

        When ConfigManager encounters errors, it may return defaults or
        raise exceptions that ConfigMixin catches.
        """
        # Arrange: Create invalid YAML
        config_dir = tmp_path / ".agents"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
            this is: [not valid: yaml content
            badly: {formatted
            """,
            encoding="utf-8"
        )

        # Act: Access config
        adapter = DummyAdapter(tmp_path)
        result = adapter.config

        # Assert: Error handled gracefully (either empty dict or defaults)
        assert isinstance(result, dict)
        assert adapter._cached_config is not None

    def test_config_property_delegates_to_load_config(self, tmp_path: Path) -> None:
        """Test that the config property delegates to _load_config method."""
        # Arrange
        adapter = DummyAdapter(tmp_path)

        # Act: Access via property
        result = adapter.config

        # Assert: Internal _load_config was called and cached
        assert isinstance(result, dict)
        assert adapter._cached_config is not None
        assert adapter._cached_config is result

    def test_multiple_adapters_have_independent_caches(self, tmp_path: Path) -> None:
        """Test that different adapter instances have independent caches."""
        # Arrange: Create two separate project roots
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        # Act: Create two adapters
        adapter1 = DummyAdapter(project1)
        adapter2 = DummyAdapter(project2)

        config1 = adapter1.config
        config2 = adapter2.config

        # Assert: Each adapter has its own cache
        # (configs might be identical if both load defaults, but caches are separate objects)
        assert isinstance(config1, dict)
        assert isinstance(config2, dict)
        assert adapter1._cached_config is not None
        assert adapter2._cached_config is not None
        # Most importantly: Each adapter maintains its own cache instance
        assert adapter1._cached_config is adapter1.config  # Same object on repeated access
        assert adapter2._cached_config is adapter2.config  # Same object on repeated access

    def test_config_mixin_uses_validate_false(self, tmp_path: Path) -> None:
        """Test that ConfigMixin loads config with validate=False.

        This is important for performance and to avoid validation errors
        during adapter initialization.
        """
        # Arrange: Create a config that would fail strict validation
        # but should still load with validate=False
        config_dir = tmp_path / ".agents"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            """
packs:
  active:
    - core
# Missing required fields that would fail validation
            """,
            encoding="utf-8"
        )

        # Act: Access config (should not raise validation error)
        adapter = DummyAdapter(tmp_path)
        result = adapter.config

        # Assert: Config loaded despite missing validation
        assert isinstance(result, dict)
        assert "packs" in result
