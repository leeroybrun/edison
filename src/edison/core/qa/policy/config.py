"""Preset configuration loader.

Loads validation presets from YAML configuration files.
Supports pack-extensible configuration via ConfigManager overlay system.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any

from edison.core.config import ConfigManager
from .models import ValidationPreset


class PresetConfigLoader:
    """Loads validation presets from configuration.

    Reads presets from validation.presets in the merged configuration.
    Supports pack-extensible configuration - packs can add or override presets.

    Example:
        loader = PresetConfigLoader(project_root=Path("/my/project"))
        presets = loader.load_presets()
        quick = loader.get_preset("quick")
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the loader.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        self._project_root = project_root
        self._cfg_mgr = ConfigManager(repo_root=project_root)

    @cached_property
    def _config(self) -> dict[str, Any]:
        """Load and cache the configuration."""
        return self._cfg_mgr.load_config(validate=False)

    @cached_property
    def _validation_config(self) -> dict[str, Any]:
        """Get the validation section from config."""
        validation = self._config.get("validation", {})
        return validation if isinstance(validation, dict) else {}

    @cached_property
    def _presets_config(self) -> dict[str, dict[str, Any]]:
        """Get the presets section from config."""
        presets = self._validation_config.get("presets", {})
        return presets if isinstance(presets, dict) else {}

    @cached_property
    def _defaults_config(self) -> dict[str, Any]:
        """Get the defaults section from config."""
        defaults = self._validation_config.get("defaults", {})
        return defaults if isinstance(defaults, dict) else {}

    @cached_property
    def _escalation_config(self) -> dict[str, Any]:
        """Get the escalation section from config."""
        escalation = self._validation_config.get("escalation", {})
        return escalation if isinstance(escalation, dict) else {}

    def load_presets(self) -> dict[str, ValidationPreset]:
        """Load all presets from configuration.

        Returns:
            Dictionary mapping preset ID to ValidationPreset instance
        """
        result: dict[str, ValidationPreset] = {}
        for preset_id, preset_data in self._presets_config.items():
            if not isinstance(preset_data, dict):
                continue
            # Ensure id is set in the data
            preset_data_with_id = dict(preset_data)
            preset_data_with_id["id"] = preset_id
            result[preset_id] = ValidationPreset.from_dict(preset_data_with_id)
        return result

    def get_preset(self, preset_id: str) -> ValidationPreset | None:
        """Get a specific preset by ID.

        Args:
            preset_id: Preset identifier

        Returns:
            ValidationPreset if found, None otherwise
        """
        presets = self.load_presets()
        return presets.get(preset_id)

    def get_default_preset_id(self) -> str:
        """Get the default preset ID from configuration.

        Returns:
            Default preset ID, or "standard" if not configured
        """
        default = self._defaults_config.get("preset")
        if default:
            return str(default)
        return "standard"

    def get_escalation_config(self) -> dict[str, Any]:
        """Get escalation configuration.

        Returns:
            Dictionary with escalation patterns:
            - code_patterns: File patterns that trigger code-level escalation
            - config_patterns: File patterns for config-level escalation
        """
        return dict(self._escalation_config)

    def list_preset_ids(self) -> list[str]:
        """List all available preset IDs.

        Returns:
            Sorted list of preset identifiers
        """
        return sorted(self._presets_config.keys())


__all__ = ["PresetConfigLoader"]
