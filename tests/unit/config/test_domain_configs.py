"""Tests for domain-specific config modules.

TDD: RED - Write failing tests first, then implement.
Tests PacksConfig, CompositionConfig, and caching behavior.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Dict, List


class TestPacksConfig:
    """Tests for PacksConfig domain-specific module."""
    
    def test_packs_config_returns_active_packs(self, tmp_path: Path) -> None:
        """PacksConfig should return active packs list."""
        from edison.core.config.domains import PacksConfig
        
        # Setup test config
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "packs.yml").write_text(
            "packs:\n  active:\n    - react\n    - prisma\n",
            encoding="utf-8",
        )
        
        packs_config = PacksConfig(repo_root=tmp_path)
        active = packs_config.active_packs
        
        assert active == ["react", "prisma"]
    
    def test_packs_config_returns_empty_list_when_no_packs(self, tmp_path: Path) -> None:
        """PacksConfig should return empty list when no packs configured."""
        from edison.core.config.domains import PacksConfig
        
        # No config file
        packs_config = PacksConfig(repo_root=tmp_path)
        
        assert packs_config.active_packs == []
    
    def test_packs_config_caches_result(self, tmp_path: Path) -> None:
        """PacksConfig should cache the result."""
        from edison.core.config.domains import PacksConfig
        
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "packs.yml").write_text(
            "packs:\n  active:\n    - react\n",
            encoding="utf-8",
        )
        
        packs_config = PacksConfig(repo_root=tmp_path)
        
        # Access twice
        first = packs_config.active_packs
        second = packs_config.active_packs
        
        # Should be same object (cached)
        assert first is second


class TestCompositionConfig:
    """Tests for CompositionConfig domain-specific module."""
    
    def test_composition_config_returns_deduplication_settings(self, tmp_path: Path) -> None:
        """CompositionConfig should return deduplication settings."""
        from edison.core.config.domains import CompositionConfig
        
        # Setup uses bundled defaults, no project config needed
        comp_config = CompositionConfig(repo_root=tmp_path)
        
        # Should return defaults from composition.yaml
        assert comp_config.shingle_size >= 8
        assert comp_config.min_shingles >= 1
        assert 0 < comp_config.threshold <= 1.0
    
    def test_composition_config_returns_output_paths(self, tmp_path: Path) -> None:
        """CompositionConfig should return output path configuration."""
        from edison.core.config.domains import CompositionConfig
        
        comp_config = CompositionConfig(repo_root=tmp_path)
        
        # Should have outputs configuration
        outputs = comp_config.outputs
        assert outputs is not None
        assert "canonical_entry" in outputs or "agents" in outputs
    
    def test_composition_config_caches_result(self, tmp_path: Path) -> None:
        """CompositionConfig should cache loaded configuration."""
        from edison.core.config.domains import CompositionConfig
        
        comp_config = CompositionConfig(repo_root=tmp_path)
        
        # Access twice
        first = comp_config.outputs
        second = comp_config.outputs
        
        # Should be same object (cached)
        assert first is second


class TestCachedConfigManager:
    """Tests for caching behavior in ConfigManager."""
    
    def test_config_manager_caches_when_requested(self, tmp_path: Path) -> None:
        """ConfigManager should cache config when using get_cached_config."""
        from edison.core.config import get_cached_config
        
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "project.yml").write_text(
            "project:\n  name: test-project\n",
            encoding="utf-8",
        )
        
        # Get config twice
        first = get_cached_config(repo_root=tmp_path)
        second = get_cached_config(repo_root=tmp_path)
        
        # Should be same object (cached)
        assert first is second
    
    def test_config_manager_clear_cache(self, tmp_path: Path) -> None:
        """clear_all_caches should invalidate cached config."""
        from edison.core.config import get_cached_config, clear_all_caches
        
        first = get_cached_config(repo_root=tmp_path)
        clear_all_caches()
        second = get_cached_config(repo_root=tmp_path)
        
        # Should be different objects after cache clear
        assert first is not second
