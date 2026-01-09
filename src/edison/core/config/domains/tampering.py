"""Domain-specific configuration for tampering protection.

Provides cached access to tampering protection settings including:
- Enabled state
- Protection mode (deny-write, deny-all, etc.)
- Protected directory path
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict

from ..base import BaseDomainConfig
from edison.core.utils.io import read_yaml, write_yaml
from edison.core.utils.paths import get_project_config_dir, get_management_paths


class TamperingConfig(BaseDomainConfig):
    """Tampering protection configuration accessor.

    Reads the `tampering` section from project config. Configuration is loaded
    from `{config_dir}/config/tampering.yaml` if present.
    """

    def __init__(self, repo_root: Path | None = None, *, include_packs: bool = True) -> None:
        """Initialize tampering config.

        Args:
            repo_root: Repository root path. Uses auto-detection if None.
            include_packs: Whether to include pack config overlays (default: True).
        """
        self._repo_root_param = repo_root
        super().__init__(repo_root, include_packs=include_packs)
        # Load tampering-specific config from dedicated file
        self._tampering_config = self._load_tampering_config()

    def _config_section(self) -> str:
        return "tampering"

    def _get_config_file_path(self) -> Path:
        """Get the path to the tampering config file."""
        config_dir = get_project_config_dir(self.repo_root, create=False)
        return config_dir / "config" / "tampering.yaml"

    def _load_tampering_config(self) -> Dict[str, Any]:
        """Load tampering-specific configuration from dedicated file."""
        config_path = self._get_config_file_path()
        if not config_path.exists():
            return {}
        data = read_yaml(config_path, default={})
        if isinstance(data, dict):
            return data.get("tampering", {}) or {}
        return {}

    @cached_property
    def enabled(self) -> bool:
        """Check if tampering protection is enabled.

        Returns:
            True if tampering protection is enabled, False otherwise.
        """
        # Check tampering-specific config first, then fall back to merged config
        if "enabled" in self._tampering_config:
            return bool(self._tampering_config.get("enabled", False))
        return bool(self.section.get("enabled", False))

    @cached_property
    def mode(self) -> str:
        """Get the tampering protection mode.

        Returns:
            Protection mode string (e.g., 'deny-write', 'deny-all').
        """
        if "mode" in self._tampering_config:
            raw = self._tampering_config.get("mode")
        else:
            raw = self.section.get("mode")
        value = str(raw).strip() if raw is not None else ""
        return value or "deny-write"

    @cached_property
    def protected_dir(self) -> Path:
        """Get the protected directory path.

        Returns:
            Path to the protected directory.
        """
        if "protectedDir" in self._tampering_config:
            raw = self._tampering_config.get("protectedDir")
        else:
            raw = self.section.get("protectedDir")

        if raw is not None:
            value = str(raw).strip()
            if value:
                return Path(value)

        # Default: _protected under management root
        mgmt = get_management_paths(self.repo_root)
        return mgmt.get_management_root() / "_protected"

    def set_enabled(self, value: bool) -> None:
        """Set the enabled state and write to config file.

        Args:
            value: True to enable tampering protection, False to disable.
        """
        config_path = self._get_config_file_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config
        existing: Dict[str, Any] = {}
        if config_path.exists():
            data = read_yaml(config_path, default={})
            if isinstance(data, dict):
                existing = data

        # Update tampering section
        tampering_section = existing.get("tampering", {}) or {}
        if not isinstance(tampering_section, dict):
            tampering_section = {}
        tampering_section["enabled"] = value
        existing["tampering"] = tampering_section

        # Write atomically
        write_yaml(config_path, existing)

        # Invalidate cached properties for this instance
        self._tampering_config = self._load_tampering_config()
        # Clear cached_property values
        for attr in ("enabled", "mode", "protected_dir"):
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Get current tampering protection status.

        Returns:
            Dictionary with current configuration state.
        """
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "protectedDir": str(self.protected_dir),
        }


__all__ = ["TamperingConfig"]
