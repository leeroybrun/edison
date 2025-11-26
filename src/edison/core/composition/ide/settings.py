#!/usr/bin/env python3
from __future__ import annotations

"""Compose Claude Code settings.json payload."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from edison.core.utils.io import read_json, write_json_atomic, ensure_dir
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
    def load_core_settings(self) -> Dict:
        path = self.core_dir / "config" / "settings.yaml"
        if not path.exists():
            path = self.core_dir / "config" / "settings.yml"
        data = self.cfg_mgr.load_yaml(path) if path.exists() else {}
        return (data.get("settings") or {}).get("claude", {}) if isinstance(data, dict) else {}

    def _load_pack_settings(self, pack: str) -> Dict:
        path = self.packs_dir / pack / "config" / "settings.yml"
        if not path.exists():
            path = self.packs_dir / pack / "config" / "settings.yaml"
        data = self.cfg_mgr.load_yaml(path) if path.exists() else {}
        return (data.get("settings") or {}).get("claude", {}) if isinstance(data, dict) else {}

    def _load_project_settings(self) -> Dict:
        path = self.project_config_dir / "settings.yml"
        if not path.exists():
            path = self.project_config_dir / "settings.yaml"
        data = self.cfg_mgr.load_yaml(path) if path.exists() else {}
        return (data.get("settings") or {}).get("claude", {}) if isinstance(data, dict) else {}

    def extract_pack_permissions(self, pack: str) -> Dict:
        settings = self._load_pack_settings(pack)
        return settings.get("permissions", {}) if isinstance(settings, dict) else {}

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
        """Return settings dictionary ready to write to settings.json."""
        settings = self.load_core_settings()

        # Merge pack overlays
        for pack in self._active_packs():
            pack_settings = self._load_pack_settings(pack)
            settings = self.deep_merge_settings(settings, pack_settings)

        # Merge project overrides
        project_settings = self._load_project_settings()
        settings = self.deep_merge_settings(settings, project_settings)

        # Include hooks section when hooks are enabled
        if (self.config.get("hooks") or {}).get("enabled"):
            try:
                from .hooks import HookComposer

                hook_composer = HookComposer(self.config, self.repo_root)
                if hasattr(hook_composer, "generate_settings_json_hooks_section"):
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
        ensure_dir(target.parent)

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
                    settings = self.deep_merge_settings(settings, existing)

        write_json_atomic(target, settings, indent=2)
        return target


__all__ = ["SettingsComposer", "merge_permissions"]
