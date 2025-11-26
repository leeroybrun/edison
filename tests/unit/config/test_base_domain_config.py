"""Tests for BaseDomainConfig abstract base class.

TDD: RED - Write failing tests first, then implement.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict


class TestBaseDomainConfig:
    """Tests for BaseDomainConfig base class."""

    def test_base_config_is_abstract(self) -> None:
        """BaseDomainConfig cannot be instantiated directly."""
        from edison.core.config.base import BaseDomainConfig
        
        with pytest.raises(TypeError):
            BaseDomainConfig()  # type: ignore

    def test_concrete_config_requires_config_section(self, tmp_path: Path) -> None:
        """Concrete subclass must implement _config_section."""
        from edison.core.config.base import BaseDomainConfig
        
        class IncompleteConfig(BaseDomainConfig):
            pass
        
        with pytest.raises(TypeError):
            IncompleteConfig(repo_root=tmp_path)

    def test_concrete_config_accesses_section(self, tmp_path: Path) -> None:
        """Concrete subclass can access its config section."""
        from edison.core.config.base import BaseDomainConfig
        
        # Create minimal project config
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "test.yml").write_text(
            "mySection:\n  key: value\n  nested:\n    inner: data\n",
            encoding="utf-8",
        )
        
        class MyConfig(BaseDomainConfig):
            def _config_section(self) -> str:
                return "mySection"
        
        cfg = MyConfig(repo_root=tmp_path)
        assert cfg.section.get("key") == "value"
        assert cfg.section.get("nested", {}).get("inner") == "data"

    def test_repo_root_property(self, tmp_path: Path) -> None:
        """Config exposes repo_root property."""
        from edison.core.config.base import BaseDomainConfig
        
        class MyConfig(BaseDomainConfig):
            def _config_section(self) -> str:
                return "test"
        
        cfg = MyConfig(repo_root=tmp_path)
        assert cfg.repo_root == tmp_path

    def test_full_config_accessible(self, tmp_path: Path) -> None:
        """Full config dict is accessible via _config."""
        from edison.core.config.base import BaseDomainConfig
        
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "project.yml").write_text(
            "project:\n  name: test-project\n",
            encoding="utf-8",
        )
        
        class MyConfig(BaseDomainConfig):
            def _config_section(self) -> str:
                return "project"
        
        cfg = MyConfig(repo_root=tmp_path)
        assert "project" in cfg._config

    def test_section_returns_empty_dict_for_missing_section(self, tmp_path: Path) -> None:
        """Section returns empty dict when config section doesn't exist."""
        from edison.core.config.base import BaseDomainConfig
        
        class MyConfig(BaseDomainConfig):
            def _config_section(self) -> str:
                return "nonExistentSection"
        
        cfg = MyConfig(repo_root=tmp_path)
        assert cfg.section == {}


class TestCentralizedCache:
    """Tests for centralized config caching."""

    def test_get_cached_config_returns_same_instance(self, tmp_path: Path) -> None:
        """get_cached_config returns same dict for same repo_root."""
        from edison.core.config.cache import get_cached_config, clear_all_caches
        
        clear_all_caches()
        
        first = get_cached_config(repo_root=tmp_path)
        second = get_cached_config(repo_root=tmp_path)
        
        assert first is second

    def test_clear_all_caches_invalidates(self, tmp_path: Path) -> None:
        """clear_all_caches invalidates the cache."""
        from edison.core.config.cache import get_cached_config, clear_all_caches
        
        first = get_cached_config(repo_root=tmp_path)
        clear_all_caches()
        second = get_cached_config(repo_root=tmp_path)
        
        assert first is not second

    def test_different_repo_roots_get_different_configs(self, tmp_path: Path) -> None:
        """Different repo roots get different cached configs."""
        from edison.core.config.cache import get_cached_config, clear_all_caches
        
        clear_all_caches()
        
        path1 = tmp_path / "project1"
        path2 = tmp_path / "project2"
        path1.mkdir()
        path2.mkdir()
        
        config1 = get_cached_config(repo_root=path1)
        config2 = get_cached_config(repo_root=path2)
        
        assert config1 is not config2
