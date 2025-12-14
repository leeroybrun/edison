"""Compose Claude Code settings.json payload.

This module generates settings.json for Claude Code using ConfigManager's
pack-aware configuration loading (core > packs > project).

All merging is handled by ConfigManager's unified deep_merge. For array
concatenation (e.g., permissions), use the ["+", item1, item2] syntax in YAML.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from edison.core.utils.io import read_json, write_json_atomic, ensure_directory
from edison.core.utils.merge import deep_merge
from .base import AdapterComponent, AdapterContext


# Keys that are Edison's internal control flags and should NOT be written to Claude Code settings.json
# These are used for Edison's generation/merge logic but are not valid Claude Code settings
EDISON_INTERNAL_KEYS: Set[str] = {
    "enabled",
    "generate",
    "preserve_custom",
    "backup_before",
    "platforms",
}


class SettingsComposer(AdapterComponent):
    """Build settings payload (platform-agnostic).

    Uses ConfigManager's pack-aware loading for unified configuration.
    No specialized merge logic - all merging is handled by ConfigManager.
    """

    def __init__(self, context: AdapterContext) -> None:
        super().__init__(context)
        self.project_config_dir = self.project_dir / "config"

    # ----- Loaders -----
    def load_merged_settings(self) -> Dict[str, Any]:
        """Load settings using ConfigManager's pack-aware loading.

        ConfigManager handles the full layering:
        1. Core config (bundled settings.yaml)
        2. Pack configs (bundled + project packs)
        3. Project config (.edison/config/settings.yaml)

        Returns:
            Merged settings.claude configuration dict
        """
        from edison.core.config import ConfigManager

        # Use ConfigManager's unified pack-aware loading
        cfg_mgr = ConfigManager(repo_root=self.project_root)
        full_config = cfg_mgr.load_config(validate=False, include_packs=True)
        settings_section = full_config.get("settings", {}) or {}
        return settings_section.get("claude", {}) if isinstance(settings_section, dict) else {}

    def load_core_settings(self) -> Dict[str, Any]:
        """Load core settings only (without packs/project)."""
        from edison.core.config import ConfigManager

        cfg_mgr = ConfigManager(repo_root=self.project_root)
        from edison.core.utils.profiling import span

        with span("settings.load_core_settings"):
            full_config = cfg_mgr.load_config(validate=False, include_packs=False)
        settings_section = full_config.get("settings", {}) or {}
        return settings_section.get("claude", {}) if isinstance(settings_section, dict) else {}

    # ----- Composition -----
    def compose_settings(self) -> Dict[str, Any]:
        """Return settings dictionary ready to write to settings.json.

        Uses ConfigManager's pack-aware loading for core > packs > project layering.
        All merging is handled by ConfigManager's unified deep_merge.
        """
        # Get settings from ConfigManager (already merged core > packs > project)
        settings = self.load_merged_settings()

        # Include hooks section (HookComposer loads defaults from bundled config)
        try:
            from .hooks import HookComposer

            hook_composer = HookComposer(self.context)
            hooks_cfg = hook_composer._hooks_cfg()
            if hooks_cfg.get("enabled", True) is not False:
                hooks_section = hook_composer.generate_settings_json_hooks_section()
                if hooks_section:
                    settings["hooks"] = hooks_section
        except Exception:
            pass

        # Strip Edison internal control keys that are not valid Claude Code settings
        for key in EDISON_INTERNAL_KEYS:
            settings.pop(key, None)

        # Flatten explicit data payload if provided
        if isinstance(settings.get("data"), dict):
            data_block = settings.pop("data")
            settings = deep_merge(settings, data_block)

        return settings

    # AdapterComponent contract -------------------------------------------------

    def compose(self) -> Dict[str, Any]:
        """Compose settings payload (platform-agnostic)."""
        return self.compose_settings()

    def sync(self, output_dir: Path) -> List[Path]:
        """Write settings.json into ``output_dir`` and return written paths."""
        target = Path(output_dir) / "settings.json"
        ensure_directory(target.parent)
        settings = self.compose_settings()
        write_json_atomic(target, settings, indent=2)
        return [target]

    def _claude_config(self) -> Dict[str, Any]:
        return (self.config.get("settings") or {}).get("claude", {}) if isinstance(self.config, dict) else {}

    def write_settings_file(self) -> Path:
        """Write settings.json to .claude/, merging with existing file if present."""
        settings = self.compose_settings()
        target = self.project_root / ".claude" / "settings.json"
        ensure_directory(target.parent)

        claude_cfg = self._claude_config()

        # If file exists and preserve_custom is enabled, merge with existing
        if target.exists():
            # Always backup before modifying
            if claude_cfg.get("backup_before", True):
                backup = target.with_suffix(".json.bak")
                backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

            # Load existing settings
            existing = read_json(target, default=None)
            if isinstance(existing, dict):
                # Merge composed settings INTO existing (existing takes precedence)
                # This preserves user customizations
                if claude_cfg.get("preserve_custom", True):
                    settings = deep_merge(settings, existing)

        write_json_atomic(target, settings, indent=2)
        return target


__all__ = ["SettingsComposer"]
