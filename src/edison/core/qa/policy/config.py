"""Preset configuration loading from YAML.

Loads validation presets from the merged config (core -> packs -> project).
Uses ConfigManager for proper layered config loading.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Optional

from edison.core.config import ConfigManager
from edison.core.qa.policy.models import ValidationPreset


class PresetConfigLoader:
    """Loads validation presets from configuration.

    Presets are loaded from validation.presets section in the merged config.
    The config is layered: bundled defaults -> packs -> project overrides.

    Example config (validation.yaml):
        validation:
          presets:
            quick:
              name: quick
              validators: [global-codex]
              required_evidence: []
              blocking_validators: [global-codex]
              description: "Minimal validation for docs-only tasks"
            standard:
              name: standard
              validators: [global-codex, security, performance]
              required_evidence: [command-test.txt, command-lint.txt]
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize preset config loader.

        Args:
            project_root: Optional project root path. Auto-detected if not provided.
        """
        self._project_root = project_root
        self._cfg_mgr: Optional[ConfigManager] = None

    @property
    def project_root(self) -> Path:
        """Get project root, resolving lazily if needed."""
        if self._project_root is None:
            from edison.core.utils.paths import PathResolver
            self._project_root = PathResolver.resolve_project_root()
        return self._project_root

    @property
    def _config_manager(self) -> ConfigManager:
        """Get ConfigManager instance (lazy init)."""
        if self._cfg_mgr is None:
            self._cfg_mgr = ConfigManager(repo_root=self.project_root)
        return self._cfg_mgr

    @cached_property
    def _config(self) -> dict[str, Any]:
        """Load and cache the full config."""
        return self._config_manager.load_config(validate=False)

    @cached_property
    def _validation_config(self) -> dict[str, Any]:
        """Get the validation section from config."""
        cfg = self._config.get("validation", {})
        return cfg if isinstance(cfg, dict) else {}

    @cached_property
    def _presets_config(self) -> dict[str, dict[str, Any]]:
        """Get the presets section from validation config."""
        presets = self._validation_config.get("presets", {})
        return presets if isinstance(presets, dict) else {}

    def load_presets(self) -> dict[str, ValidationPreset]:
        """Load all validation presets from config.

        Returns:
            Dict mapping preset name to ValidationPreset instance
        """
        result: dict[str, ValidationPreset] = {}

        for name, config in self._presets_config.items():
            preset = self._parse_preset(name, config)
            if preset:
                result[name] = preset

        return result

    def get_preset(self, name: str) -> Optional[ValidationPreset]:
        """Get a specific preset by name.

        Args:
            name: Preset name (e.g., "quick", "standard")

        Returns:
            ValidationPreset if found, None otherwise
        """
        presets = self.load_presets()
        return presets.get(name)

    def load_inference_rules(self) -> list[dict[str, Any]]:
        """Load preset inference rules from config.

        Returns:
            List of inference rule dicts with pattern/preset mappings
        """
        inference_config = self._validation_config.get("presetInference", {})
        if not isinstance(inference_config, dict):
            return []

        rules = inference_config.get("rules", [])
        if not isinstance(rules, list):
            return []

        return [r for r in rules if isinstance(r, dict)]

    def _parse_preset(self, name: str, config: dict[str, Any]) -> Optional[ValidationPreset]:
        """Parse a preset from config dict.

        Args:
            name: Preset name
            config: Preset configuration dict

        Returns:
            ValidationPreset instance or None if invalid
        """
        if not isinstance(config, dict):
            return None

        validators = config.get("validators", [])
        if not isinstance(validators, list):
            validators = []
        validators = [str(v) for v in validators if v]

        required_evidence: list[str] | None
        required_present = "required_evidence" in config
        if not required_present:
            required_evidence = None
        else:
            raw_required = config.get("required_evidence")
            if raw_required is None or not isinstance(raw_required, list):
                # Fail-closed: config is invalid if key is present but not a list.
                raise ValueError(
                    f"Preset '{name}' has invalid required_evidence (expected list, got {type(raw_required).__name__})"
                )
            required_evidence = [str(e) for e in raw_required if e]

        stale_evidence = str(config.get("stale_evidence", "warn") or "warn").strip().lower()

        description = str(config.get("description", ""))
        blocking_present = "blocking_validators" in config
        raw_blocking = config.get("blocking_validators") if blocking_present else None
        if raw_blocking is None and not blocking_present:
            blocking_validators = None
        else:
            blocking_validators = raw_blocking if isinstance(raw_blocking, list) else []
            blocking_validators = [str(v) for v in blocking_validators if v]

        return ValidationPreset(
            name=name,
            validators=validators,
            required_evidence=required_evidence,
            stale_evidence=stale_evidence,
            blocking_validators=blocking_validators,
            description=description,
        )


__all__ = ["PresetConfigLoader"]
