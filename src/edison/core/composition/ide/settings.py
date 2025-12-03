#!/usr/bin/env python3
from __future__ import annotations

"""Compose Claude Code settings.json payload."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from edison.core.utils.io import read_json
from .base import IDEComposerBase

# Keys that are Edison's internal control flags and should NOT be written to Claude Code settings.json
# These are used for Edison's generation/merge logic but are not valid Claude Code settings
EDISON_INTERNAL_KEYS: Set[str] = {
    "enabled",
    "generate",
    "preserve_custom",
    "backup_before",
    "platforms",
}


def merge_permissions(base: Dict, overlay: Dict) -> Dict:
    """Merge permissions by concatenating arrays and de-duplicating."""
    result: Dict[str, List[str]] = {"allow": [], "deny": [], "ask": []}
    for key in ("allow", "deny", "ask"):
        seen = set()
        merged: List[str] = []
        for src in (base.get(key, []), overlay.get(key, [])):
            if not isinstance(src, list):
                continue
            for item in src:
                if item in seen:
                    continue
                seen.add(item)
                merged.append(str(item))
        result[key] = merged
    return result


class SettingsComposer(IDEComposerBase):
    """Build settings payload for Claude Code client."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        super().__init__(config=config, repo_root=repo_root)
        self.project_config_dir = self.project_dir / "config"

    # ----- Loaders -----
    def load_all_settings(self) -> Dict:
        """Load and merge settings from all layers with special permissions/env handling.

        Returns the merged 'settings.claude' section from core → packs → project.

        Note: Uses manual layered loading instead of _load_layered_config() because
        settings require special merge behavior for permissions (array concat) and env (dict merge).
        """
        settings: Dict = {}

        # Helper to extract claude settings from loaded data
        def extract_claude_settings(data: Dict) -> Dict:
            if isinstance(data, dict):
                settings_section = data.get("settings") or {}
                if isinstance(settings_section, dict):
                    return settings_section.get("claude", {}) or {}
            return {}

        # 1. Core layer
        core_file = self.core_dir / "config" / "settings.yaml"
        if not core_file.exists():
            core_file = self.core_dir / "config" / "settings.yml"
        if core_file.exists():
            core_data = extract_claude_settings(self.load_yaml_safe(core_file))
            settings = self.deep_merge_settings(settings, core_data)

        # 2. Pack layers
        for pack in self.get_active_packs():
            # Bundled pack
            pack_file = self.bundled_packs_dir / pack / "config" / "settings.yaml"
            if not pack_file.exists():
                pack_file = self.bundled_packs_dir / pack / "config" / "settings.yml"
            if pack_file.exists():
                pack_data = extract_claude_settings(self.load_yaml_safe(pack_file))
                settings = self.deep_merge_settings(settings, pack_data)

            # Project pack (if exists)
            project_pack_file = self.project_packs_dir / pack / "config" / "settings.yaml"
            if not project_pack_file.exists():
                project_pack_file = self.project_packs_dir / pack / "config" / "settings.yml"
            if project_pack_file.exists():
                project_pack_data = extract_claude_settings(self.load_yaml_safe(project_pack_file))
                settings = self.deep_merge_settings(settings, project_pack_data)

        # 3. Project layer
        project_file = self.project_dir / "config" / "settings.yaml"
        if not project_file.exists():
            project_file = self.project_dir / "config" / "settings.yml"
        if project_file.exists():
            project_data = extract_claude_settings(self.load_yaml_safe(project_file))
            settings = self.deep_merge_settings(settings, project_data)

        return settings

    def extract_pack_permissions(self, pack: str) -> Dict:
        """Extract permissions from a specific pack's settings.

        Note: This method loads from a single pack, not using layered loading.
        """
        # Load single pack settings (not layered)
        pack_file = self.bundled_packs_dir / pack / "config" / "settings.yaml"
        if not pack_file.exists():
            pack_file = self.bundled_packs_dir / pack / "config" / "settings.yml"

        if pack_file.exists():
            data = self.load_yaml_safe(pack_file)
            if isinstance(data, dict):
                settings_section = data.get("settings") or {}
                if isinstance(settings_section, dict):
                    claude_settings = settings_section.get("claude", {}) or {}
                    if isinstance(claude_settings, dict):
                        return claude_settings.get("permissions", {}) or {}

        return {}

    # ----- Merging helpers -----
    def deep_merge_settings(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge settings dicts with special handling for permissions/env."""
        result: Dict = dict(base)
        for key, value in (overlay or {}).items():
            if key == "permissions":
                base_perms = result.get("permissions", {}) if isinstance(result.get("permissions"), dict) else {}
                result["permissions"] = merge_permissions(base_perms, value if isinstance(value, dict) else {})
            elif key == "env":
                base_env = result.get("env", {}) if isinstance(result.get("env"), dict) else {}
                overlay_env = value if isinstance(value, dict) else {}
                merged_env = dict(base_env)
                merged_env.update(overlay_env)
                result["env"] = merged_env
            elif isinstance(result.get(key), dict) and isinstance(value, dict):
                result[key] = self.deep_merge_settings(result[key], value)
            else:
                result[key] = value
        return result

    # ----- Composition -----
    def compose_settings(self) -> Dict:
        """Return settings dictionary ready to write to settings.json.

        Uses unified _load_layered_config() to load from all layers.
        Note: The special merging for permissions/env is handled by deep_merge
        in the config manager during layered loading.
        """
        # Load all settings using unified layered config
        settings = self.load_all_settings()

        # Include hooks section (HookComposer loads defaults from bundled config)
        try:
            from .hooks import HookComposer

            hook_composer = HookComposer(self.config, self.repo_root)
            hooks_cfg = hook_composer._hooks_cfg()
            # Check if hooks are enabled (defaults to True from bundled config)
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
            settings = self.deep_merge_settings(settings, data_block)

        return settings

    def _claude_config(self) -> Dict:
        return (self.config.get("settings") or {}).get("claude", {}) if isinstance(self.config, dict) else {}

    def write_settings_file(self) -> Path:
        """Write settings.json to .claude/, merging with existing file if present."""
        settings = self.compose_settings()
        target = self.repo_root / ".claude" / "settings.json"

        claude_cfg = self._claude_config()

        # If file exists and preserve_custom is enabled, merge with existing
        if target.exists():
            # Always backup before modifying
            if claude_cfg.get("backup_before", True):
                backup = target.with_suffix(".json.bak")
                self.writer.write_text(backup, target.read_text(encoding="utf-8"))

            # Load existing settings
            existing = read_json(target, default=None)
            if isinstance(existing, dict):
                # Merge composed settings INTO existing (existing takes precedence)
                # This preserves user customizations
                if claude_cfg.get("preserve_custom", True):
                    settings = self.deep_merge_settings(settings, existing)

        written_path = self.writer.write_json(target, settings, indent=2)
        return written_path


__all__ = ["SettingsComposer", "merge_permissions"]



