"""Tests for TamperingConfig domain module.

TDD: RED - These tests should FAIL until implementation is complete.
Tests config loading with tampering.enabled, protectedDir, and mode settings.
"""
from __future__ import annotations

import pytest
from pathlib import Path


class TestTamperingConfigDefaults:
    """Tests for TamperingConfig default values."""

    def test_tampering_disabled_by_default(self, tmp_path: Path) -> None:
        """Tampering protection should be disabled by default."""
        from edison.core.config.domains.tampering import TamperingConfig

        config = TamperingConfig(repo_root=tmp_path)

        assert config.enabled is False

    def test_tampering_mode_defaults_to_deny_write(self, tmp_path: Path) -> None:
        """Default mode should be 'deny-write'."""
        from edison.core.config.domains.tampering import TamperingConfig

        config = TamperingConfig(repo_root=tmp_path)

        assert config.mode == "deny-write"

    def test_tampering_protected_dir_defaults_to_protected(self, tmp_path: Path) -> None:
        """Default protected directory should be _protected under project management dir."""
        from edison.core.config.domains.tampering import TamperingConfig

        config = TamperingConfig(repo_root=tmp_path)

        # Should end with _protected (actual path depends on project management dir)
        assert config.protected_dir.name == "_protected"


class TestTamperingConfigFromYaml:
    """Tests for loading TamperingConfig from YAML."""

    def test_tampering_enabled_from_config(self, tmp_path: Path) -> None:
        """Should read enabled=true from config file."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "tampering.yaml").write_text(
            "tampering:\n  enabled: true\n",
            encoding="utf-8",
        )

        config = TamperingConfig(repo_root=tmp_path)

        assert config.enabled is True

    def test_tampering_mode_from_config(self, tmp_path: Path) -> None:
        """Should read mode from config file."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "tampering.yaml").write_text(
            "tampering:\n  enabled: true\n  mode: deny-all\n",
            encoding="utf-8",
        )

        config = TamperingConfig(repo_root=tmp_path)

        assert config.mode == "deny-all"

    def test_tampering_protected_dir_from_config(self, tmp_path: Path) -> None:
        """Should read protectedDir from config file."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        custom_dir = tmp_path / "custom_protected"
        (config_dir / "tampering.yaml").write_text(
            f"tampering:\n  enabled: true\n  protectedDir: {custom_dir}\n",
            encoding="utf-8",
        )

        config = TamperingConfig(repo_root=tmp_path)

        assert config.protected_dir == custom_dir


class TestTamperingConfigCaching:
    """Tests for TamperingConfig caching behavior."""

    def test_tampering_config_caches_result(self, tmp_path: Path) -> None:
        """TamperingConfig should cache loaded values."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "tampering.yaml").write_text(
            "tampering:\n  enabled: true\n",
            encoding="utf-8",
        )

        config = TamperingConfig(repo_root=tmp_path)

        # Access twice
        first = config.enabled
        second = config.enabled

        # Should return same value (stable)
        assert first == second


class TestTamperingConfigMethods:
    """Tests for TamperingConfig helper methods."""

    def test_set_enabled_writes_config(self, tmp_path: Path) -> None:
        """set_enabled should write to config file."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        config = TamperingConfig(repo_root=tmp_path)
        config.set_enabled(True)

        # Reload and verify
        config2 = TamperingConfig(repo_root=tmp_path)
        assert config2.enabled is True

    def test_set_enabled_false_writes_config(self, tmp_path: Path) -> None:
        """set_enabled(False) should disable tampering protection."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "tampering.yaml").write_text(
            "tampering:\n  enabled: true\n",
            encoding="utf-8",
        )

        config = TamperingConfig(repo_root=tmp_path)
        config.set_enabled(False)

        # Reload and verify
        config2 = TamperingConfig(repo_root=tmp_path)
        assert config2.enabled is False

    def test_get_status_returns_dict(self, tmp_path: Path) -> None:
        """get_status should return a dictionary with current state."""
        from edison.core.config.domains.tampering import TamperingConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "tampering.yaml").write_text(
            "tampering:\n  enabled: true\n  mode: deny-write\n",
            encoding="utf-8",
        )

        config = TamperingConfig(repo_root=tmp_path)
        status = config.get_status()

        assert isinstance(status, dict)
        assert status["enabled"] is True
        assert status["mode"] == "deny-write"
        assert "protectedDir" in status
