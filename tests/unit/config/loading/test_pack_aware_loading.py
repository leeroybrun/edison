"""Tests for pack-aware configuration loading.

This module tests the two-phase config loading that enables packs
to override any configuration section.

Layering order (lowest to highest priority):
1. Core config (bundled defaults)
2. Pack configs (bundled packs + project packs)
3. Project config
4. Environment overrides
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config import ConfigManager
from edison.core.config.cache import get_cached_config, clear_all_caches, is_cached


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear config caches before each test."""
    clear_all_caches()
    yield
    clear_all_caches()


class TestBootstrapPacks:
    """Tests for _get_bootstrap_packs method."""

    def test_extracts_active_packs_from_config(self, tmp_path: Path) -> None:
        """Bootstrap should extract active packs from packs.active."""
        mgr = ConfigManager(tmp_path)
        cfg = {"packs": {"active": ["react", "python", "prisma"]}}
        result = mgr._get_bootstrap_packs(cfg)
        assert result == ["react", "python", "prisma"]

    def test_returns_empty_list_when_no_packs_section(self, tmp_path: Path) -> None:
        """Should return empty list when packs section is missing."""
        mgr = ConfigManager(tmp_path)
        cfg = {"other": "config"}
        result = mgr._get_bootstrap_packs(cfg)
        assert result == []

    def test_returns_empty_list_when_packs_active_is_none(self, tmp_path: Path) -> None:
        """Should return empty list when packs.active is None."""
        mgr = ConfigManager(tmp_path)
        cfg = {"packs": {"active": None}}
        result = mgr._get_bootstrap_packs(cfg)
        assert result == []

    def test_returns_empty_list_when_packs_active_is_not_list(
        self, tmp_path: Path
    ) -> None:
        """Should return empty list when packs.active is not a list."""
        mgr = ConfigManager(tmp_path)
        cfg = {"packs": {"active": "not-a-list"}}
        result = mgr._get_bootstrap_packs(cfg)
        assert result == []

    def test_filters_out_empty_pack_names(self, tmp_path: Path) -> None:
        """Should filter out empty or falsy pack names."""
        mgr = ConfigManager(tmp_path)
        cfg = {"packs": {"active": ["react", "", None, "python"]}}
        result = mgr._get_bootstrap_packs(cfg)
        assert result == ["react", "python"]


class TestLoadDirectory:
    """Tests for _load_directory helper method."""

    def test_loads_yaml_files_alphabetically(self, tmp_path: Path) -> None:
        """Should load YAML files in alphabetical order."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "a.yaml").write_text("section_a:\n  key: value_a\n")
        (config_dir / "b.yaml").write_text("section_b:\n  key: value_b\n")

        mgr = ConfigManager(tmp_path)
        cfg = mgr._load_directory(config_dir, {})

        assert cfg["section_a"]["key"] == "value_a"
        assert cfg["section_b"]["key"] == "value_b"

    def test_merges_overlapping_keys(self, tmp_path: Path) -> None:
        """Should merge overlapping keys from multiple files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "a.yaml").write_text("shared:\n  first: 1\n  second: 2\n")
        (config_dir / "b.yaml").write_text("shared:\n  second: 22\n  third: 3\n")

        mgr = ConfigManager(tmp_path)
        cfg = mgr._load_directory(config_dir, {})

        # b.yaml should override shared.second but keep shared.first
        assert cfg["shared"]["first"] == 1
        assert cfg["shared"]["second"] == 22
        assert cfg["shared"]["third"] == 3

    def test_handles_nonexistent_directory(self, tmp_path: Path) -> None:
        """Should return unchanged config for nonexistent directory."""
        mgr = ConfigManager(tmp_path)
        initial = {"existing": "config"}
        cfg = mgr._load_directory(tmp_path / "nonexistent", initial)
        assert cfg == {"existing": "config"}

    def test_handles_both_yaml_and_yml_extensions(self, tmp_path: Path) -> None:
        """Should load both .yaml and .yml files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "a.yaml").write_text("from_yaml: true\n")
        (config_dir / "b.yml").write_text("from_yml: true\n")

        mgr = ConfigManager(tmp_path)
        cfg = mgr._load_directory(config_dir, {})

        assert cfg["from_yaml"] is True
        assert cfg["from_yml"] is True


class TestLoadPackConfigs:
    """Tests for _load_pack_configs method."""

    def test_loads_bundled_pack_config(self, tmp_path: Path) -> None:
        """Should load config from bundled packs."""
        # Create bundled pack structure
        bundled_pack = tmp_path / "bundled_packs" / "test-pack" / "config"
        bundled_pack.mkdir(parents=True)
        (bundled_pack / "custom.yaml").write_text("custom:\n  from_pack: true\n")

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"
        mgr.project_packs_dir = tmp_path / "project_packs"  # Doesn't exist

        cfg = mgr._load_pack_configs({}, ["test-pack"])
        assert cfg["custom"]["from_pack"] is True

    def test_project_pack_overrides_bundled_pack(self, tmp_path: Path) -> None:
        """Project pack config should override bundled pack config."""
        # Create bundled pack
        bundled_pack = tmp_path / "bundled_packs" / "test-pack" / "config"
        bundled_pack.mkdir(parents=True)
        (bundled_pack / "custom.yaml").write_text(
            "custom:\n  source: bundled\n  bundled_only: true\n"
        )

        # Create project pack (overrides bundled)
        project_pack = tmp_path / "project_packs" / "test-pack" / "config"
        project_pack.mkdir(parents=True)
        (project_pack / "custom.yaml").write_text(
            "custom:\n  source: project\n  project_only: true\n"
        )

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"
        mgr.project_packs_dir = tmp_path / "project_packs"

        cfg = mgr._load_pack_configs({}, ["test-pack"])

        # Project should override source
        assert cfg["custom"]["source"] == "project"
        # But bundled-only should be merged
        assert cfg["custom"]["bundled_only"] is True
        assert cfg["custom"]["project_only"] is True

    def test_loads_multiple_packs_in_order(self, tmp_path: Path) -> None:
        """Should load multiple packs in specified order."""
        # Create two bundled packs
        pack_a = tmp_path / "bundled_packs" / "pack-a" / "config"
        pack_a.mkdir(parents=True)
        (pack_a / "shared.yaml").write_text("shared:\n  value: from_pack_a\n")

        pack_b = tmp_path / "bundled_packs" / "pack-b" / "config"
        pack_b.mkdir(parents=True)
        (pack_b / "shared.yaml").write_text("shared:\n  value: from_pack_b\n")

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"
        mgr.project_packs_dir = tmp_path / "project_packs"

        # Later packs override earlier packs
        cfg = mgr._load_pack_configs({}, ["pack-a", "pack-b"])
        assert cfg["shared"]["value"] == "from_pack_b"

        # Clear and test reverse order
        cfg = mgr._load_pack_configs({}, ["pack-b", "pack-a"])
        assert cfg["shared"]["value"] == "from_pack_a"


class TestLoadConfigWithPacks:
    """Tests for full load_config with pack support."""

    def test_include_packs_true_by_default(self, tmp_path: Path) -> None:
        """load_config should include packs by default."""
        # Check the default value
        import inspect

        sig = inspect.signature(ConfigManager.load_config)
        include_packs_param = sig.parameters.get("include_packs")
        assert include_packs_param is not None
        assert include_packs_param.default is True

    def test_project_config_overrides_pack_config(self, tmp_path: Path) -> None:
        """Project config should always override pack config."""
        # Create pack config
        pack_config = tmp_path / "bundled_packs" / "test-pack" / "config"
        pack_config.mkdir(parents=True)
        (pack_config / "custom.yaml").write_text(
            "custom:\n  source: pack\n  pack_only: true\n"
        )

        # Create project config (should win)
        project_config = tmp_path / ".edison" / "config"
        project_config.mkdir(parents=True)
        (project_config / "custom.yaml").write_text(
            "custom:\n  source: project\n  project_only: true\n"
        )

        # Create packs.yaml to activate the test pack
        (project_config / "packs.yaml").write_text(
            "packs:\n  active:\n    - test-pack\n"
        )

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"

        cfg = mgr.load_config(validate=False, include_packs=True)

        # Project should override source
        assert cfg["custom"]["source"] == "project"
        # Pack-only should still be merged
        assert cfg["custom"]["pack_only"] is True
        assert cfg["custom"]["project_only"] is True

    def test_include_packs_false_skips_pack_loading(self, tmp_path: Path) -> None:
        """Setting include_packs=False should skip pack config loading."""
        # Create pack config
        pack_config = tmp_path / "bundled_packs" / "test-pack" / "config"
        pack_config.mkdir(parents=True)
        (pack_config / "custom.yaml").write_text("from_pack: true\n")

        # Create project config with active packs
        project_config = tmp_path / ".edison" / "config"
        project_config.mkdir(parents=True)
        (project_config / "packs.yaml").write_text(
            "packs:\n  active:\n    - test-pack\n"
        )

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"

        # With packs
        cfg_with_packs = mgr.load_config(validate=False, include_packs=True)
        assert cfg_with_packs.get("from_pack") is True

        # Without packs
        cfg_without_packs = mgr.load_config(validate=False, include_packs=False)
        assert cfg_without_packs.get("from_pack") is None


class TestCacheWithPacks:
    """Tests for cache.py with include_packs support."""

    def test_separate_cache_keys_for_packs_vs_no_packs(self, tmp_path: Path) -> None:
        """Cache should use different keys for packs vs no_packs."""
        from edison.core.config.cache import _cache_key

        key_with_packs = _cache_key(tmp_path, include_packs=True)
        key_without_packs = _cache_key(tmp_path, include_packs=False)

        assert key_with_packs != key_without_packs
        assert ":packs" in key_with_packs
        assert ":no_packs" in key_without_packs

    def test_get_cached_config_respects_include_packs(self, tmp_path: Path) -> None:
        """get_cached_config should respect include_packs parameter."""
        # Create pack config
        pack_config = tmp_path / "bundled_packs" / "test-pack" / "config"
        pack_config.mkdir(parents=True)
        (pack_config / "custom.yaml").write_text("from_pack: true\n")

        # Create project config with active packs
        project_config = tmp_path / ".edison" / "config"
        project_config.mkdir(parents=True)
        (project_config / "packs.yaml").write_text(
            "packs:\n  active:\n    - test-pack\n"
        )

        # Monkey-patch bundled_packs_dir for ConfigManager
        original_init = ConfigManager.__init__

        def patched_init(self, repo_root=None):
            original_init(self, repo_root)
            self.bundled_packs_dir = tmp_path / "bundled_packs"

        ConfigManager.__init__ = patched_init
        try:
            cfg_with_packs = get_cached_config(
                tmp_path, validate=False, include_packs=True
            )
            cfg_without_packs = get_cached_config(
                tmp_path, validate=False, include_packs=False
            )

            assert cfg_with_packs.get("from_pack") is True
            assert cfg_without_packs.get("from_pack") is None
        finally:
            ConfigManager.__init__ = original_init

    def test_is_cached_respects_include_packs(self, tmp_path: Path) -> None:
        """is_cached should check for correct cache key based on include_packs."""
        # Initially nothing is cached
        assert is_cached(tmp_path, include_packs=True) is False
        assert is_cached(tmp_path, include_packs=False) is False

        # Cache with packs
        get_cached_config(tmp_path, validate=False, include_packs=True)
        assert is_cached(tmp_path, include_packs=True) is True
        assert is_cached(tmp_path, include_packs=False) is False

        # Cache without packs
        get_cached_config(tmp_path, validate=False, include_packs=False)
        assert is_cached(tmp_path, include_packs=True) is True
        assert is_cached(tmp_path, include_packs=False) is True


class TestPackOverrideAnySection:
    """Tests that packs can override any config section."""

    def test_pack_can_override_qa_config(self, tmp_path: Path) -> None:
        """Packs should be able to override QA settings."""
        pack_config = tmp_path / "bundled_packs" / "python" / "config"
        pack_config.mkdir(parents=True)
        (pack_config / "qa.yaml").write_text(
            "qa:\n  customPythonSetting: enabled\n"
        )

        project_config = tmp_path / ".edison" / "config"
        project_config.mkdir(parents=True)
        (project_config / "packs.yaml").write_text(
            "packs:\n  active:\n    - python\n"
        )

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"

        cfg = mgr.load_config(validate=False)
        assert cfg.get("qa", {}).get("customPythonSetting") == "enabled"

    def test_pack_can_override_session_config(self, tmp_path: Path) -> None:
        """Packs should be able to override session settings."""
        pack_config = tmp_path / "bundled_packs" / "react" / "config"
        pack_config.mkdir(parents=True)
        (pack_config / "session.yaml").write_text(
            "session:\n  reactSpecific: true\n"
        )

        project_config = tmp_path / ".edison" / "config"
        project_config.mkdir(parents=True)
        (project_config / "packs.yaml").write_text(
            "packs:\n  active:\n    - react\n"
        )

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"

        cfg = mgr.load_config(validate=False)
        assert cfg.get("session", {}).get("reactSpecific") is True

    def test_pack_can_override_timeouts(self, tmp_path: Path) -> None:
        """Packs should be able to override timeout settings."""
        pack_config = tmp_path / "bundled_packs" / "prisma" / "config"
        pack_config.mkdir(parents=True)
        (pack_config / "timeouts.yaml").write_text(
            "timeouts:\n  database:\n    migration: 600\n"
        )

        project_config = tmp_path / ".edison" / "config"
        project_config.mkdir(parents=True)
        (project_config / "packs.yaml").write_text(
            "packs:\n  active:\n    - prisma\n"
        )

        mgr = ConfigManager(tmp_path)
        mgr.bundled_packs_dir = tmp_path / "bundled_packs"

        cfg = mgr.load_config(validate=False)
        assert cfg.get("timeouts", {}).get("database", {}).get("migration") == 600









